"""
============================================================================
 TRAIN FINAL (kandidat produksi) -- ARSITEKTUR SKENARIO -- trainv2
============================================================================
Arsitektur final (keputusan skripsi):

    harga = Prophet( trend + yearly + lebaran
                     + harga_gkg + curah_hujan + produksi_padi + inflasi_pangan )
            + XGBoost( residual | fitur autoregresif saja )

- Variabel eksternal = REGRESSOR PROPHET (additive, standardized, teregularisasi).
- XGBoost = korektor residual, HANYA fitur autoregresif (tanpa exog):
      residual_lag_1, residual_lag_2, lag_1, lag_2, rolling_mean_3,
      month_sin, month_cos
- Mode SKENARIO: prediksi diberikan kondisi eksternal yang diasumsikan.

Skrip ini:
  1. Melaporkan rolling backtest 2024/25/26 (bukti untuk Bab IV).
  2. Melatih model FINAL pada SELURUH data 2021..2026.
  3. Menyimpan artefak KANDIDAT ke trainv2 dengan suffix _scenario
     (TIDAK menimpa produksi backend/ml_models maupun pkl lama).
        prophet_model_scenario.pkl
        xgb_model_scenario.pkl
        features_scenario.json
        metrics_final_scenario.json

Deploy (Tahap 2, MANUAL setelah disetujui): salin ke backend/ml_models/ sbg
prophet_model.pkl, best_xgb_model.pkl, features.json.

Jalankan:
    backend/.venv/Scripts/python.exe \
        backend/data_train/hybrid_model/trainv2/train_final_scenario.py
============================================================================
"""

import os
import json
import logging
import warnings

import numpy as np
import pandas as pd
import joblib

# pyrefly: ignore [missing-import]
from prophet import Prophet
from prophet.utilities import regressor_coefficients
from sklearn.metrics import (mean_absolute_percentage_error,
                             mean_absolute_error, root_mean_squared_error)
from xgboost import XGBRegressor

warnings.filterwarnings("ignore")
logging.getLogger("cmdstanpy").setLevel(logging.ERROR)
logging.getLogger("prophet").setLevel(logging.ERROR)

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
# dataset final: utamakan salinan kanonik di backend/data (yang juga dipakai
# seed_db), lalu salinan lokal trainv2, lalu lokasi datasets.
_CANDIDATES = [
    os.path.abspath(os.path.join(SCRIPT_DIR, "..", "..", "..", "..",
                                 "backend", "data", "harga_beras_2018_2026.csv")),
    os.path.join(SCRIPT_DIR, "harga_beras_2018_2026.csv"),
    os.path.abspath(os.path.join(SCRIPT_DIR, "..", "..", "datasets", "data_app",
                                 "harga_beras_2018_2026.csv")),
]
DATA_PATH = next((p for p in _CANDIDATES if os.path.exists(p)), _CANDIDATES[0])

START_YEAR = 2021
BACKTEST_YEARS = [2024, 2025, 2026]
PROPHET_CPS, PROPHET_SPS, PROPHET_MODE = 0.5, 10.0, "multiplicative"
REG_PRIOR_SCALE = 2.0
EXOG = ["harga_gkg", "curah_hujan", "produksi_padi", "inflasi_pangan"]
REGRESSORS = ["lebaran"] + EXOG

XGB_FEATS = ["residual_lag_1", "residual_lag_2", "lag_1", "lag_2",
             "rolling_mean_3", "month_sin", "month_cos"]
# Hyperparameter hasil RandomizedSearchCV pada ARSITEKTUR FINAL
# (tune_xgb_final.py: Prophet+exog residual, 7 fitur AR).
XGB_PARAMS = dict(subsample=0.8, reg_lambda=0.5, reg_alpha=0.1, n_estimators=200,
                  min_child_weight=3, max_depth=3, learning_rate=0.01,
                  gamma=0, colsample_bytree=0.8)
RANDOM_STATE = 42


def mape(y, p):
    return mean_absolute_percentage_error(y, p)


def load_pool():
    pool = pd.read_csv(DATA_PATH)
    pool["tanggal"] = pd.to_datetime(pool["tanggal"])
    pool = pool.sort_values("tanggal").reset_index(drop=True)
    return pool[pool["tanggal"].dt.year >= START_YEAR].reset_index(drop=True)


def fit_prophet(train_df):
    m = Prophet(yearly_seasonality=True, weekly_seasonality=False,
                daily_seasonality=False, changepoint_prior_scale=PROPHET_CPS,
                seasonality_prior_scale=PROPHET_SPS, seasonality_mode=PROPHET_MODE)
    for r in REGRESSORS:
        if r == "lebaran":
            m.add_regressor("lebaran")
        else:
            m.add_regressor(r, prior_scale=REG_PRIOR_SCALE, standardize=True,
                            mode="additive")
    cols = ["tanggal", "harga_beras"] + REGRESSORS
    p = train_df[cols].rename(columns={"tanggal": "ds", "harga_beras": "y"})
    m.fit(p)
    return m


def prophet_yhat(model, frame):
    cols = ["tanggal"] + REGRESSORS
    return model.predict(frame[cols].rename(columns={"tanggal": "ds"}))["yhat"].values


def add_ar_features(frame):
    f = frame.copy()
    f["lag_1"] = f["harga_beras"].shift(1)
    f["lag_2"] = f["harga_beras"].shift(2)
    f["rolling_mean_3"] = f["harga_beras"].shift(1).rolling(3).mean()
    f["residual_lag_1"] = f["residual"].shift(1)
    f["residual_lag_2"] = f["residual"].shift(2)
    mth = f["tanggal"].dt.month
    f["month_sin"] = np.sin(2 * np.pi * mth / 12)
    f["month_cos"] = np.cos(2 * np.pi * mth / 12)
    return f


# ===========================================================================
print("=" * 78)
print("TRAIN FINAL (kandidat) -- arsitektur SKENARIO: Prophet(+4 exog) + XGBoost")
print("=" * 78)
pool = load_pool()
print(f"Data: {pool['tanggal'].min().date()}..{pool['tanggal'].max().date()} "
      f"({len(pool)} baris)\n")

# ---- 1. ROLLING BACKTEST (bukti Bab IV) -----------------------------------
print("ROLLING BACKTEST (expanding window):")
print(f"{'tahun':<8}{'Prophet-base':>14}{'Hybrid 1-step':>15}{'Hybrid recursive':>18}")
all_a, all_b, all_h, all_r = [], [], [], []
per_year = {}
for ty in BACKTEST_YEARS:
    window = pool[pool["tanggal"].dt.year <= ty].reset_index(drop=True)
    train = window[window["tanggal"].dt.year < ty]
    if (window["tanggal"].dt.year == ty).sum() == 0 or len(train) < 12:
        continue
    model = fit_prophet(train)
    window["yhat"] = prophet_yhat(model, window)
    window["residual"] = window["harga_beras"] - window["yhat"]
    window = add_ar_features(window)
    tr = window[window["tanggal"].dt.year < ty].dropna(subset=XGB_FEATS)
    te = window[window["tanggal"].dt.year == ty].reset_index(drop=True)

    xgb = XGBRegressor(random_state=RANDOM_STATE, **XGB_PARAMS)
    xgb.fit(tr[XGB_FEATS], tr["residual"])

    actual = te["harga_beras"].values
    base = te["yhat"].values
    hybrid = base + xgb.predict(te[XGB_FEATS])

    # recursive
    hp = list(window[window["tanggal"].dt.year < ty]["harga_beras"].values)
    hr = list(window[window["tanggal"].dt.year < ty]["residual"].dropna().values)
    rec = []
    for i in range(len(te)):
        row = te.iloc[[i]].copy()
        row["lag_1"] = hp[-1]; row["lag_2"] = hp[-2]
        row["rolling_mean_3"] = np.mean(hp[-3:])
        row["residual_lag_1"] = hr[-1]; row["residual_lag_2"] = hr[-2]
        pr = float(xgb.predict(row[XGB_FEATS])[0])
        pp = base[i] + pr
        rec.append(pp); hp.append(pp); hr.append(pr)
    rec = np.array(rec)

    per_year[ty] = {"base": mape(actual, base), "hybrid": mape(actual, hybrid),
                    "recursive": mape(actual, rec)}
    print(f"{ty:<8}{per_year[ty]['base']:>13.2%}{per_year[ty]['hybrid']:>14.2%}"
          f"{per_year[ty]['recursive']:>17.2%}")
    all_a += list(actual); all_b += list(base); all_h += list(hybrid); all_r += list(rec)

agg = {"base": mape(all_a, all_b), "hybrid": mape(all_a, all_h),
       "recursive": mape(all_a, all_r),
       "base_mae": mean_absolute_error(all_a, all_b),
       "base_rmse": root_mean_squared_error(all_a, all_b),
       "hybrid_mae": mean_absolute_error(all_a, all_h),
       "hybrid_rmse": root_mean_squared_error(all_a, all_h)}
print("-" * 78)
print(f"{'AGREGAT':<8}{agg['base']:>13.2%}{agg['hybrid']:>14.2%}"
      f"{agg['recursive']:>17.2%}   MAE={agg['hybrid_mae']:.1f} "
      f"RMSE={agg['hybrid_rmse']:.1f}")

# ---- 2. MODEL FINAL (seluruh data 2021..2026) -----------------------------
print("\n" + "=" * 78)
print("MELATIH MODEL FINAL pada SELURUH data 2021..2026 ...")
prophet_final = fit_prophet(pool)
full = pool.copy()
full["yhat"] = prophet_yhat(prophet_final, full)
full["residual"] = full["harga_beras"] - full["yhat"]
full = add_ar_features(full).dropna(subset=XGB_FEATS).reset_index(drop=True)
xgb_final = XGBRegressor(random_state=RANDOM_STATE, **XGB_PARAMS)
xgb_final.fit(full[XGB_FEATS], full["residual"])

coefs = regressor_coefficients(prophet_final)
print("\nKontribusi regressor (model final, standardized):")
print(coefs[["regressor", "regressor_mode", "center", "coef"]].to_string(index=False))
print("\nXGBoost feature importance (residual, fitur autoregresif):")
imp = pd.DataFrame({"f": XGB_FEATS, "imp": xgb_final.feature_importances_})
print(imp.sort_values("imp", ascending=False).to_string(index=False))

# ---- 3. SIMPAN ARTEFAK KANDIDAT (suffix _scenario) ------------------------
joblib.dump(prophet_final, os.path.join(SCRIPT_DIR, "prophet_model_scenario.pkl"))
joblib.dump(xgb_final, os.path.join(SCRIPT_DIR, "xgb_model_scenario.pkl"))
with open(os.path.join(SCRIPT_DIR, "features_scenario.json"), "w") as f:
    json.dump({"features": XGB_FEATS}, f, indent=4)

summary = {
    "architecture": "Prophet(lebaran+4exog regressor) + XGBoost(residual, AR features)",
    "mode": "scenario (exog kontemporer diasumsikan diketahui)",
    "data_range": [str(pool["tanggal"].min().date()), str(pool["tanggal"].max().date())],
    "prophet": {"cps": PROPHET_CPS, "sps": PROPHET_SPS, "mode": PROPHET_MODE,
                "reg_prior_scale": REG_PRIOR_SCALE, "regressors": REGRESSORS},
    "xgb_features": XGB_FEATS, "xgb_params": XGB_PARAMS,
    "backtest_per_year": per_year, "backtest_aggregate": agg,
    "regressor_coefficients": coefs[["regressor", "coef"]].to_dict(orient="records"),
    "leakage_note": "exog coincident; dgn lag-1 MAPE ~9.91% (lihat experiment_final_check.json)",
}
with open(os.path.join(SCRIPT_DIR, "metrics_final_scenario.json"), "w") as f:
    json.dump(summary, f, indent=4, default=float)

print("\n" + "=" * 78)
print("Artefak KANDIDAT tersimpan di trainv2 (produksi TIDAK disentuh):")
print("  prophet_model_scenario.pkl, xgb_model_scenario.pkl,")
print("  features_scenario.json, metrics_final_scenario.json")
print("=" * 78)
