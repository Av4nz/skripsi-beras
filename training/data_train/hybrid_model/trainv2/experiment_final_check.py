"""
============================================================================
 VERIFIKASI FINAL (read-only) -- trainv2
============================================================================
Dua uji untuk mengunci keputusan arsitektur, TANPA menyentuh produksi:

  UJI 1 -- Perbandingan residual learner di atas base Prophet+exog (config C):
           none (base) vs Linear AR(1) vs XGBoost.
           => apakah XGBoost 'inert-aman' lebih layak daripada AR(1) yang
              tidak stabil, ketika exog sudah ada di Prophet?

  UJI 2 -- Robustness kebocoran skenario:
           config C dengan exog KONTEMPORER (nilai bulan target, seperti
           eksperimen sebelumnya) vs exog LAG-1 (nilai bulan sebelumnya, yang
           benar-benar diketahui saat memprediksi).
           => berapa akurasi yang bertahan tanpa asumsi 'exog masa depan
              diketahui'?

Prophet config = yang dideploy (cps=0.5, sps=10, multiplicative); exog additive
+ standardized + prior_scale=2.0. Rolling backtest 2024/2025/2026.

Jalankan:
    backend/.venv/Scripts/python.exe \
        backend/data_train/hybrid_model/trainv2/experiment_final_check.py
============================================================================
"""

import os
import json
import logging
import warnings

import numpy as np
import pandas as pd

# pyrefly: ignore [missing-import]
from prophet import Prophet
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_percentage_error
from xgboost import XGBRegressor

warnings.filterwarnings("ignore")
logging.getLogger("cmdstanpy").setLevel(logging.ERROR)
logging.getLogger("prophet").setLevel(logging.ERROR)

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_PATH = os.path.abspath(
    os.path.join(SCRIPT_DIR, "..", "..", "datasets", "data_app",
                 "harga_beras_2018_2026.csv")
)

START_YEAR = 2021
BACKTEST_YEARS = [2024, 2025, 2026]
PROPHET_CPS, PROPHET_SPS, PROPHET_MODE = 0.5, 10.0, "multiplicative"
REG_PRIOR_SCALE = 2.0
EXOG = ["harga_gkg", "curah_hujan", "produksi_padi", "inflasi_pangan"]
REGRESSORS_C = ["lebaran"] + EXOG

# XGBoost residual: fitur autoregresif (exog TIDAK di sini, sudah di Prophet).
XGB_FEATS = ["residual_lag_1", "residual_lag_2", "lag_1", "lag_2",
             "rolling_mean_3", "month_sin", "month_cos"]
XGB_PARAMS = dict(subsample=0.7, reg_lambda=5.0, reg_alpha=0, n_estimators=30,
                  min_child_weight=7, max_depth=4, learning_rate=0.1,
                  gamma=1.0, colsample_bytree=1.0)
RANDOM_STATE = 42


def mape(y, p):
    return mean_absolute_percentage_error(y, p)


def load_pool():
    pool = pd.read_csv(DATA_PATH)
    pool["tanggal"] = pd.to_datetime(pool["tanggal"])
    pool = pool.sort_values("tanggal").reset_index(drop=True)
    return pool[pool["tanggal"].dt.year >= START_YEAR].reset_index(drop=True)


def fit_prophet(train_df, regressors):
    m = Prophet(yearly_seasonality=True, weekly_seasonality=False,
                daily_seasonality=False, changepoint_prior_scale=PROPHET_CPS,
                seasonality_prior_scale=PROPHET_SPS, seasonality_mode=PROPHET_MODE)
    for r in regressors:
        if r == "lebaran":
            m.add_regressor("lebaran")
        else:
            m.add_regressor(r, prior_scale=REG_PRIOR_SCALE, standardize=True,
                            mode="additive")
    cols = ["tanggal", "harga_beras"] + regressors
    p = train_df[cols].rename(columns={"tanggal": "ds", "harga_beras": "y"})
    m.fit(p)
    return m


def prophet_yhat(model, frame, regressors):
    cols = ["tanggal"] + regressors
    return model.predict(frame[cols].rename(columns={"tanggal": "ds"}))["yhat"].values


def fit_ar1(resid_train):
    r = np.asarray(resid_train, float)
    lr = LinearRegression().fit(r[:-1].reshape(-1, 1), r[1:])
    return float(lr.intercept_), float(lr.coef_[0])


# ===========================================================================
# UJI 1 : residual learner di atas base Prophet+exog (config C)
# ===========================================================================
def uji1_year(pool, test_year):
    window = pool[pool["tanggal"].dt.year <= test_year].reset_index(drop=True)
    train = window[window["tanggal"].dt.year < test_year]
    if len(window[window["tanggal"].dt.year == test_year]) == 0 or len(train) < 12:
        return None

    model = fit_prophet(train, REGRESSORS_C)
    window["yhat"] = prophet_yhat(model, window, REGRESSORS_C)
    window["residual"] = window["harga_beras"] - window["yhat"]

    # fitur autoregresif untuk XGBoost
    window["lag_1"] = window["harga_beras"].shift(1)
    window["lag_2"] = window["harga_beras"].shift(2)
    window["rolling_mean_3"] = window["harga_beras"].shift(1).rolling(3).mean()
    window["residual_lag_1"] = window["residual"].shift(1)
    window["residual_lag_2"] = window["residual"].shift(2)
    mth = window["tanggal"].dt.month
    window["month_sin"] = np.sin(2 * np.pi * mth / 12)
    window["month_cos"] = np.cos(2 * np.pi * mth / 12)

    te = window["tanggal"].dt.year == test_year
    tr = window["tanggal"].dt.year < test_year
    actual = window.loc[te, "harga_beras"].values
    yhat_te = window.loc[te, "yhat"].values
    resid_tr = window.loc[tr, "residual"].values
    resid_te = window.loc[te, "residual"].values

    out = {"actual": actual, "base": yhat_te}

    # --- AR(1) ---
    icpt, phi = fit_ar1(resid_tr)
    seq = np.concatenate([resid_tr, resid_te])
    n_tr = len(resid_tr)
    ar_one = np.array([yhat_te[i] + icpt + phi * seq[n_tr + i - 1]
                       for i in range(len(resid_te))])
    ar_rec, rp = [], resid_tr[-1]
    for i in range(len(resid_te)):
        rh = icpt + phi * rp
        ar_rec.append(yhat_te[i] + rh)
        rp = rh
    out["ar_onestep"] = ar_one
    out["ar_recursive"] = np.array(ar_rec)
    out["phi"] = phi

    # --- XGBoost ---
    xtr = window[tr].dropna(subset=XGB_FEATS)
    xgb = XGBRegressor(random_state=RANDOM_STATE, **XGB_PARAMS)
    xgb.fit(xtr[XGB_FEATS], xtr["residual"])
    te_df = window[te].copy()
    xgb_one = yhat_te + xgb.predict(te_df[XGB_FEATS])

    # recursive XGBoost: propagate harga & residual
    hp = list(window.loc[tr, "harga_beras"].values)
    hr = list(resid_tr)
    xgb_rec = []
    te_idx = window[te].reset_index(drop=True)
    for i in range(len(te_idx)):
        row = te_idx.iloc[[i]].copy()
        row["lag_1"] = hp[-1]
        row["lag_2"] = hp[-2]
        row["rolling_mean_3"] = np.mean(hp[-3:])
        row["residual_lag_1"] = hr[-1]
        row["residual_lag_2"] = hr[-2]
        pr = float(xgb.predict(row[XGB_FEATS])[0])
        pp = yhat_te[i] + pr
        xgb_rec.append(pp)
        hp.append(pp)
        hr.append(pr)
    out["xgb_onestep"] = xgb_one
    out["xgb_recursive"] = np.array(xgb_rec)
    return out


# ===========================================================================
# UJI 2 : exog kontemporer vs exog lag-1
# ===========================================================================
def uji2_year(pool, test_year, lag_exog):
    p = pool.copy()
    regs = ["lebaran"] + EXOG
    if lag_exog:
        for c in EXOG:
            p[c] = p[c].shift(1)
        p = p.dropna(subset=EXOG).reset_index(drop=True)
    window = p[p["tanggal"].dt.year <= test_year].reset_index(drop=True)
    train = window[window["tanggal"].dt.year < test_year]
    te = window["tanggal"].dt.year == test_year
    if te.sum() == 0 or len(train) < 12:
        return None
    model = fit_prophet(train, regs)
    window["yhat"] = prophet_yhat(model, window, regs)
    return window.loc[te, "harga_beras"].values, window.loc[te, "yhat"].values


# ===========================================================================
print("=" * 78)
print("VERIFIKASI FINAL [read-only]")
print("=" * 78)
pool = load_pool()

# ---- UJI 1 ----
print("\nUJI 1: residual learner di atas base Prophet+exog (config C)")
print("-" * 78)
s1 = {ty: uji1_year(pool, ty) for ty in BACKTEST_YEARS}
s1 = {k: v for k, v in s1.items() if v is not None}

def pooled1(key):
    a, p = [], []
    for ty in s1:
        a.extend(s1[ty]["actual"]); p.extend(s1[ty][key])
    return np.array(a), np.array(p)

print(f"{'Residual learner':<24}{'one-step':>12}{'recursive':>12}")
rows1 = {}
for label, konesep, krec in [
    ("none (base)", "base", "base"),
    ("Linear AR(1)", "ar_onestep", "ar_recursive"),
    ("XGBoost", "xgb_onestep", "xgb_recursive"),
]:
    a, one = pooled1(konesep)
    _, rec = pooled1(krec)
    rows1[label] = {"onestep": mape(a, one), "recursive": mape(a, rec)}
    print(f"{label:<24}{mape(a, one):>11.2%}{mape(a, rec):>12.2%}")

print("\nPer tahun (one-step):")
print(f"{'tahun':<8}{'base':>9}{'AR(1)':>9}{'XGBoost':>10}{'phi_AR':>9}")
for ty in s1:
    r = s1[ty]
    print(f"{ty:<8}{mape(r['actual'], r['base']):>8.2%}"
          f"{mape(r['actual'], r['ar_onestep']):>9.2%}"
          f"{mape(r['actual'], r['xgb_onestep']):>10.2%}{r['phi']:>9.3f}")

# ---- UJI 2 ----
print("\n" + "=" * 78)
print("UJI 2: exog KONTEMPORER vs exog LAG-1 (base Prophet+exog, config C)")
print("-" * 78)
rows2 = {}
for tag, lag in [("kontemporer (t)", False), ("lag-1 (t-1, diketahui)", True)]:
    a_all, p_all, per = [], [], {}
    for ty in BACKTEST_YEARS:
        res = uji2_year(pool, ty, lag)
        if res is None:
            continue
        a, p = res
        per[ty] = mape(a, p)
        a_all.extend(a); p_all.extend(p)
    agg = mape(np.array(a_all), np.array(p_all))
    rows2[tag] = {"aggregate": agg, "per_year": per}
    per_str = "  ".join(f"{ty}:{v:.2%}" for ty, v in per.items())
    print(f"  exog {tag:<24} agg={agg:.2%}   ({per_str})")

# ---- simpan ----
out = {
    "uji1_residual_learner": rows1,
    "uji1_phi_per_year": {ty: s1[ty]["phi"] for ty in s1},
    "uji2_leakage_scenario": rows2,
}
with open(os.path.join(SCRIPT_DIR, "experiment_final_check.json"), "w") as f:
    json.dump(out, f, indent=4, default=float)
print("\nTersimpan: experiment_final_check.json")
print("=" * 78)
