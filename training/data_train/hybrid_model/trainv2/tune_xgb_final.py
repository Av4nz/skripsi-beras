"""
============================================================================
 RE-TUNING XGBOOST untuk ARSITEKTUR FINAL (read-only) -- trainv2
============================================================================
Men-tuning ulang hyperparameter XGBoost KHUSUS pada konfigurasi final:
  - residual = harga - Prophet(lebaran + 4 regressor eksternal)
  - fitur XGBoost = 7 fitur autoregresif (tanpa exog)

Sebelumnya params XGBoost diwarisi dari tuning arsitektur LAMA (Prophet tanpa
exog, 11 fitur). Skrip ini memberi params yang benar-benar dituning pada setup
final -> klaim metodologi bersih untuk skripsi.

Prosedur:
  1. RandomizedSearchCV (100 iter, TimeSeriesSplit 4-fold, scoring MAE) pada
     residual final (Prophet dilatih 2021..2026).
  2. Rolling backtest 2024/25/26 membandingkan MAPE hybrid dgn:
        (a) params WARISAN (frozen saat ini), vs
        (b) params HASIL tuning ulang.
  3. Simpan params terbaik -> xgb_tuned_final.json (BELUM mengubah artefak).

Jalankan:
    backend/.venv/Scripts/python.exe \
        training/data_train/hybrid_model/trainv2/tune_xgb_final.py
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
from sklearn.model_selection import RandomizedSearchCV, TimeSeriesSplit
from sklearn.metrics import mean_absolute_percentage_error
from xgboost import XGBRegressor

warnings.filterwarnings("ignore")
logging.getLogger("cmdstanpy").setLevel(logging.ERROR)
logging.getLogger("prophet").setLevel(logging.ERROR)

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
# dataset final (setelah reorg) ada di backend/data; beberapa kandidat lokasi.
_CANDIDATES = [
    os.path.join(SCRIPT_DIR, "harga_beras_2018_2026.csv"),  # salinan lokal trainv2
    os.path.abspath(os.path.join(SCRIPT_DIR, "..", "..", "..", "..",
                                 "backend", "data", "harga_beras_2018_2026.csv")),
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
RANDOM_STATE = 42

# params warisan (frozen saat ini di produksi)
XGB_INHERITED = dict(subsample=0.7, reg_lambda=5.0, reg_alpha=0, n_estimators=30,
                     min_child_weight=7, max_depth=4, learning_rate=0.1,
                     gamma=1.0, colsample_bytree=1.0)


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


def add_ar(frame):
    f = frame.copy()
    f["lag_1"] = f["harga_beras"].shift(1)
    f["lag_2"] = f["harga_beras"].shift(2)
    f["rolling_mean_3"] = f["harga_beras"].shift(1).rolling(3).mean()
    f["residual_lag_1"] = f["residual"].shift(1)
    f["residual_lag_2"] = f["residual"].shift(2)
    m = f["tanggal"].dt.month
    f["month_sin"] = np.sin(2 * np.pi * m / 12)
    f["month_cos"] = np.cos(2 * np.pi * m / 12)
    return f


# ===========================================================================
print("=" * 78)
print("RE-TUNING XGBOOST -- arsitektur final (Prophet+exog, 7 fitur AR)")
print("=" * 78)
print("Dataset:", DATA_PATH)
pool = load_pool()

# ---- 1. Residual final (Prophet dilatih seluruh data) + fitur AR ----------
prophet_full = fit_prophet(pool)
full = pool.copy()
full["yhat"] = prophet_yhat(prophet_full, full)
full["residual"] = full["harga_beras"] - full["yhat"]
full = add_ar(full).dropna(subset=XGB_FEATS).reset_index(drop=True)
X, y = full[XGB_FEATS], full["residual"]
print(f"Data tuning residual: {len(full)} baris")

# ---- 2. RandomizedSearchCV ------------------------------------------------
param_grid = {
    "n_estimators": [30, 50, 80, 100, 150, 200],
    "learning_rate": [0.01, 0.03, 0.05, 0.1],
    "max_depth": [2, 3, 4],
    "subsample": [0.5, 0.6, 0.7, 0.8, 1.0],
    "colsample_bytree": [0.5, 0.6, 0.7, 0.8, 1.0],
    "min_child_weight": [1, 3, 5, 7],
    "gamma": [0, 0.1, 0.5, 1.0],
    "reg_alpha": [0, 0.1, 0.5, 1.0],
    "reg_lambda": [0.5, 1.0, 2.0, 5.0],
}
print("\nRandomizedSearchCV (100 iter, TimeSeriesSplit 4-fold, MAE) ...")
search = RandomizedSearchCV(
    estimator=XGBRegressor(random_state=RANDOM_STATE),
    param_distributions=param_grid, n_iter=100,
    scoring="neg_mean_absolute_error", cv=TimeSeriesSplit(n_splits=4),
    verbose=0, random_state=RANDOM_STATE, n_jobs=1,
)
search.fit(X, y)
XGB_TUNED = search.best_params_
print("Params HASIL tuning ulang:")
for k in sorted(XGB_TUNED):
    print(f"   {k:>18} = {XGB_TUNED[k]}")

# ---- 3. Rolling backtest: warisan vs tuned --------------------------------
def backtest(xgb_params):
    A, base_all, hyb_all = [], [], []
    for ty in BACKTEST_YEARS:
        window = pool[pool["tanggal"].dt.year <= ty].reset_index(drop=True)
        train = window[window["tanggal"].dt.year < ty]
        if (window["tanggal"].dt.year == ty).sum() == 0 or len(train) < 12:
            continue
        model = fit_prophet(train)
        window["yhat"] = prophet_yhat(model, window)
        window["residual"] = window["harga_beras"] - window["yhat"]
        window = add_ar(window)
        tr = window[window["tanggal"].dt.year < ty].dropna(subset=XGB_FEATS)
        te = window[window["tanggal"].dt.year == ty]
        xgb = XGBRegressor(random_state=RANDOM_STATE, **xgb_params)
        xgb.fit(tr[XGB_FEATS], tr["residual"])
        A += list(te["harga_beras"].values)
        base_all += list(te["yhat"].values)
        hyb_all += list(te["yhat"].values + xgb.predict(te[XGB_FEATS]))
    return mape(A, base_all), mape(A, hyb_all)

print("\nRolling backtest 2024-2026 (agregat):")
base_i, hyb_i = backtest(XGB_INHERITED)
base_t, hyb_t = backtest(XGB_TUNED)
print(f"   Prophet-base (sama)        : {base_i:.3%}")
print(f"   Hybrid params WARISAN      : {hyb_i:.3%}")
print(f"   Hybrid params TUNED ULANG  : {hyb_t:.3%}")
print(f"   Selisih (tuned - warisan)  : {(hyb_t - hyb_i)*100:+.3f} pp")

# ---- 4. Simpan hasil ------------------------------------------------------
out = {
    "config": "Prophet(lebaran+4exog) + XGBoost(7 fitur AR)",
    "cv": "RandomizedSearchCV 100 iter, TimeSeriesSplit(4), scoring=neg MAE",
    "xgb_inherited": XGB_INHERITED,
    "xgb_tuned_final": XGB_TUNED,
    "backtest_aggregate": {
        "prophet_base": base_i,
        "hybrid_inherited": hyb_i,
        "hybrid_tuned": hyb_t,
        "delta_pp": (hyb_t - hyb_i) * 100,
    },
}
with open(os.path.join(SCRIPT_DIR, "xgb_tuned_final.json"), "w") as f:
    json.dump(out, f, indent=4, default=float)
print("\nTersimpan: xgb_tuned_final.json (artefak produksi BELUM diubah)")
print("=" * 78)
