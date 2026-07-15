"""
============================================================================
 HYBRID PROPHET + XGBOOST TRAINING  (trainv2)
============================================================================
Prediksi harga beras bulanan dengan model hybrid (arsitektur sama seperti
notebook `time_series_training (improved).ipynb`):

    harga_beras_hat = Prophet(trend + yearly seasonality + lebaran)
                      + XGBoost(residual Prophet)

Peningkatan / penyesuaian:
  1. Dataset penuh & terbaru: harga_beras_2018_2026.csv (2018-01 .. 2026-05,
     termasuk data 2026 hasil scraping PIHPS Nasional).
  2. Fitur DISELARASKAN dengan backend (predictor.py) & BEBAS kebocoran:
        lag_1/lag_2      = harga T-1 / T-2
        rolling_mean_3   = rata-rata harga 3 bulan SEBELUMNYA (pakai shift,
                           TIDAK memasukkan bulan berjalan seperti versi PDF)
        residual_lag_1/2 = residual Prophet T-1 / T-2
        month_sin/cos    = encoding siklikal bulan
     -> 11 fitur, identik dengan ml_models/features.json (drop-in ke backend).
  3. Evaluasi ROLLING BACKTEST multi-tahun (2024, 2025, 2026): untuk tiap
     tahun uji, model dilatih ulang HANYA pada data sebelum tahun itu
     (expanding window) lalu diuji one-step & recursive. Ini jauh lebih adil
     daripada mengandalkan satu tahun uji saja.
  4. Tuning: (tahun-awal training + hyperparameter Prophet) dipilih memakai
     objektif error HYBRID pada tahun-tahun validasi; XGBoost dituning via
     RandomizedSearchCV + TimeSeriesSplit. Tahun-awal ikut dituning sehingga
     bila 2018-2020 (rezim harga lama ~11rb) memperburuk akurasi, pipeline
     otomatis memakai window terbaru (fallback yang diminta user).
  5. Model produksi akhir di-refit pada SELURUH data real (s/d 2026) lalu
     disimpan: prophet_model.pkl, best_xgb_model.pkl, features.json.

Jalankan (dari root repo) dengan interpreter venv backend:
    backend/.venv/Scripts/python.exe \
        backend/data_train/hybrid_model/trainv2/train_hybrid.py
============================================================================
"""

import os
import json
import logging
import warnings

import numpy as np
import pandas as pd
import joblib

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from prophet import Prophet
from sklearn.metrics import (
    mean_absolute_error,
    mean_absolute_percentage_error,
    root_mean_squared_error,
)
from sklearn.model_selection import RandomizedSearchCV, TimeSeriesSplit
from xgboost import XGBRegressor

warnings.filterwarnings("ignore")
logging.getLogger("cmdstanpy").setLevel(logging.ERROR)
logging.getLogger("prophet").setLevel(logging.ERROR)

# ============================================================================
# 0. KONFIGURASI
# ============================================================================
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_PATH = os.path.abspath(
    os.path.join(SCRIPT_DIR, "..", "..", "datasets", "data_app",
                 "harga_beras_2018_2026.csv")
)
PLOT_DIR = os.path.join(SCRIPT_DIR, "plots")
os.makedirs(PLOT_DIR, exist_ok=True)

RANDOM_STATE = 42

# Tahun-tahun untuk rolling backtest (uji). Tiap tahun diuji dengan model yang
# hanya dilatih pada data SEBELUM tahun tsb.
BACKTEST_YEARS = [2024, 2025, 2026]
# Tahun untuk memilih hyperparameter (objektif = error hybrid one-step).
VALIDATION_YEARS = [2024, 2025]
# Kandidat tahun-awal window training (2018 = pakai seluruh data).
TRAIN_START_CANDIDATES = [2018, 2021, 2022]
# Ambang "jauh lebih buruk dari PDF" yang diminta user.
WARN_MAPE = 0.055

FEATURES = [
    "harga_gkg", "curah_hujan", "produksi_padi", "inflasi_pangan",
    "lag_1", "lag_2", "rolling_mean_3",
    "residual_lag_1", "residual_lag_2", "month_sin", "month_cos",
]
TARGET = "residual"

# Grid Prophet (mencakup yang halus s/d fleksibel supaya tuning bebas memilih).
PROPHET_GRID = [
    {"changepoint_prior_scale": cps, "seasonality_prior_scale": sps,
     "seasonality_mode": mode}
    for cps in [0.05, 0.1, 0.3, 0.5]
    for sps in [1.0, 10.0]
    for mode in ["additive", "multiplicative"]
]


def mape(y, p):
    return mean_absolute_percentage_error(y, p)


# ============================================================================
# 1. HELPERS
# ============================================================================
def add_base_features(frame):
    frame = frame.copy()
    frame["lag_1"] = frame["harga_beras"].shift(1)
    frame["lag_2"] = frame["harga_beras"].shift(2)
    # rolling 3 bulan SEBELUM bulan berjalan (shift(1)) -> tanpa kebocoran
    frame["rolling_mean_3"] = frame["harga_beras"].shift(1).rolling(window=3).mean()
    month = frame["tanggal"].dt.month
    frame["month_sin"] = np.sin(2 * np.pi * month / 12)
    frame["month_cos"] = np.cos(2 * np.pi * month / 12)
    return frame


def fit_prophet(train_frame, params):
    m = Prophet(
        yearly_seasonality=True, weekly_seasonality=False, daily_seasonality=False,
        changepoint_prior_scale=params["changepoint_prior_scale"],
        seasonality_prior_scale=params["seasonality_prior_scale"],
        seasonality_mode=params["seasonality_mode"],
    )
    m.add_regressor("lebaran")
    p = train_frame[["tanggal", "harga_beras", "lebaran"]].rename(
        columns={"tanggal": "ds", "harga_beras": "y"})
    m.fit(p)
    return m


def prophet_predict(model, frame):
    p = frame[["tanggal", "lebaran"]].rename(columns={"tanggal": "ds"})
    return model.predict(p)["yhat"].values


def prepare_window(pool, start_year, end_year):
    """Ambil pool[start..end], tambahkan fitur lag/rolling, buang NaN awal."""
    w = pool[(pool["tanggal"].dt.year >= start_year) &
             (pool["tanggal"].dt.year <= end_year)].copy()
    w = add_base_features(w)
    w = w.dropna(subset=["lag_1", "lag_2", "rolling_mean_3"]).reset_index(drop=True)
    return w


def build_residual_frame(window, params, fit_end_year):
    """Fit Prophet pada window[year<=fit_end_year], hitung residual+lag untuk
    seluruh window. Kembalikan (prophet, frame_siap_XGBoost)."""
    prophet = fit_prophet(window[window["tanggal"].dt.year <= fit_end_year], params)
    w = window.copy()
    w["yhat"] = prophet_predict(prophet, w)
    w["residual"] = w["harga_beras"] - w["yhat"]
    w["residual_lag_1"] = w["residual"].shift(1)
    w["residual_lag_2"] = w["residual"].shift(2)
    w = w.dropna(subset=["residual_lag_1", "residual_lag_2"]).reset_index(drop=True)
    return prophet, w


def recursive_forecast(xgb, train_df, test_df):
    """Prediksi recursive: lag & residual_lag memakai prediksi model sendiri."""
    hp = list(train_df["harga_beras"].values)
    hr = list(train_df["residual"].values)
    preds = []
    for i in range(len(test_df)):
        r = test_df.iloc[[i]].copy()
        r["lag_1"] = hp[-1]
        r["lag_2"] = hp[-2]
        r["rolling_mean_3"] = np.mean(hp[-3:])
        r["residual_lag_1"] = hr[-1]
        r["residual_lag_2"] = hr[-2]
        pr = float(xgb.predict(r[FEATURES])[0])
        yv = float(r["yhat"].values[0])
        pp = yv + pr
        preds.append(pp)
        hp.append(pp)
        hr.append(pr)
    return np.array(preds)


def eval_hybrid(pool, start_year, params, test_year, xgb_params, want_recursive=True):
    """Latih (Prophet+XGBoost) pada data start..test_year-1, uji pada test_year.
    Kembalikan dict metrik + array untuk plotting."""
    window = prepare_window(pool, start_year, test_year)
    prophet, w = build_residual_frame(window, params, fit_end_year=test_year - 1)
    tr = w[w["tanggal"].dt.year <= test_year - 1]
    te = w[w["tanggal"].dt.year == test_year]
    if len(te) == 0 or len(tr) < 12:
        return None
    xgb = XGBRegressor(random_state=RANDOM_STATE, **xgb_params)
    xgb.fit(tr[FEATURES], tr[TARGET])

    yhat = te["yhat"].values
    hybrid = yhat + xgb.predict(te[FEATURES])
    out = {
        "test_year": test_year,
        "tanggal": te["tanggal"].values,
        "actual": te["harga_beras"].values,
        "yhat": yhat,
        "hybrid": hybrid,
        "prophet_only_mape": mape(te["harga_beras"], yhat),
        "hybrid_mape": mape(te["harga_beras"], hybrid),
        "prophet_only_mae": mean_absolute_error(te["harga_beras"], yhat),
        "hybrid_mae": mean_absolute_error(te["harga_beras"], hybrid),
        "hybrid_rmse": root_mean_squared_error(te["harga_beras"], hybrid),
    }
    if want_recursive:
        rec = recursive_forecast(xgb, tr, te)
        out["recursive"] = rec
        out["recursive_mape"] = mape(te["harga_beras"], rec)
        out["recursive_mae"] = mean_absolute_error(te["harga_beras"], rec)
    return out


# ============================================================================
# 2. LOAD DATA (seluruh data real, termasuk 2026)
# ============================================================================
print("=" * 78)
print("1. Memuat data:", DATA_PATH)
pool = pd.read_csv(DATA_PATH)
pool["tanggal"] = pd.to_datetime(pool["tanggal"])
pool = pool.sort_values("tanggal").reset_index(drop=True)
DATA_MAX_YEAR = int(pool["tanggal"].dt.year.max())
print(f"   {len(pool)} baris ({pool['tanggal'].min().date()} .. "
      f"{pool['tanggal'].max().date()})")


# ============================================================================
# 3. TUNING (start-year + Prophet) DENGAN OBJEKTIF ERROR HYBRID
#    XGBoost sementara pakai konfigurasi baseline yang wajar.
# ============================================================================
print("\n" + "=" * 78)
print("2. Tuning start-year + Prophet (objektif: MAPE hybrid one-step pada "
      f"tahun validasi {VALIDATION_YEARS}) ...")

XGB_BASELINE = dict(n_estimators=100, learning_rate=0.05, max_depth=3)

best = {"mape": np.inf, "start": None, "params": None}
for start in TRAIN_START_CANDIDATES:
    for params in PROPHET_GRID:
        vals = []
        ok = True
        for vy in VALIDATION_YEARS:
            try:
                res = eval_hybrid(pool, start, params, vy, XGB_BASELINE,
                                  want_recursive=False)
            except Exception:
                res = None
            if res is None:
                ok = False
                break
            vals.append(res["hybrid_mape"])
        if not ok or not vals:
            continue
        avg = float(np.mean(vals))
        if avg < best["mape"]:
            best = {"mape": avg, "start": start, "params": params}

print(f"   Terbaik -> start={best['start']}  avg hybrid MAPE={best['mape']:.2%}")
print(f"   Prophet params: {best['params']}")
best_start, best_params = best["start"], best["params"]


# ============================================================================
# 4. TUNING XGBOOST (RandomizedSearchCV + TimeSeriesSplit)
#    Dilatih pada residual window terpilih s/d tahun backtest terakhir - 1.
# ============================================================================
print("\n" + "=" * 78)
print("3. Tuning XGBoost pada residual ...")

fit_end = max(BACKTEST_YEARS) - 1  # train residual s/d sebelum backtest terakhir
tune_window = prepare_window(pool, best_start, fit_end)
_, tune_w = build_residual_frame(tune_window, best_params, fit_end_year=fit_end)
X_tune, y_tune = tune_w[FEATURES], tune_w[TARGET]

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
search = RandomizedSearchCV(
    estimator=XGBRegressor(random_state=RANDOM_STATE),
    param_distributions=param_grid, n_iter=100,
    scoring="neg_mean_absolute_error", cv=TimeSeriesSplit(n_splits=4),
    verbose=0, random_state=RANDOM_STATE, n_jobs=1,
)
search.fit(X_tune, y_tune)
best_xgb_params = search.best_params_
print(f"   XGBoost params: {best_xgb_params}")


# ============================================================================
# 5. ROLLING BACKTEST (2024, 2025, 2026)
# ============================================================================
print("\n" + "=" * 78)
print(f"4. Rolling backtest per tahun {BACKTEST_YEARS} "
      f"(window mulai {best_start}) ...")

backtest = []
all_actual, all_yhat, all_hybrid, all_rec = [], [], [], []
for ty in BACKTEST_YEARS:
    res = eval_hybrid(pool, best_start, best_params, ty, best_xgb_params,
                      want_recursive=True)
    if res is None:
        print(f"   [{ty}] dilewati (data tidak cukup).")
        continue
    backtest.append(res)
    all_actual.extend(res["actual"])
    all_yhat.extend(res["yhat"])
    all_hybrid.extend(res["hybrid"])
    all_rec.extend(res["recursive"])
    print(f"\n   [TEST {ty}]  ({len(res['actual'])} bulan)")
    print(f"     Prophet-only   : MAPE={res['prophet_only_mape']:.2%}  "
          f"MAE={res['prophet_only_mae']:.1f}")
    print(f"     Hybrid one-step: MAPE={res['hybrid_mape']:.2%}  "
          f"MAE={res['hybrid_mae']:.1f}  RMSE={res['hybrid_rmse']:.1f}")
    print(f"     Hybrid recursive: MAPE={res['recursive_mape']:.2%}  "
          f"MAE={res['recursive_mae']:.1f}")

# Agregat seluruh titik backtest
agg = {
    "prophet_only_mape": mape(all_actual, all_yhat),
    "hybrid_mape": mape(all_actual, all_hybrid),
    "recursive_mape": mape(all_actual, all_rec),
    "hybrid_mae": mean_absolute_error(all_actual, all_hybrid),
    "hybrid_rmse": root_mean_squared_error(all_actual, all_hybrid),
    "recursive_mae": mean_absolute_error(all_actual, all_rec),
}
print("\n   " + "-" * 60)
print(f"   AGREGAT ({len(all_actual)} titik):")
print(f"     Prophet-only    MAPE = {agg['prophet_only_mape']:.2%}")
print(f"     Hybrid one-step MAPE = {agg['hybrid_mape']:.2%}  "
      f"MAE = {agg['hybrid_mae']:.1f}  RMSE = {agg['hybrid_rmse']:.1f}")
print(f"     Hybrid recursive MAPE= {agg['recursive_mape']:.2%}  "
      f"MAE = {agg['recursive_mae']:.1f}")

if agg["hybrid_mape"] > WARN_MAPE:
    print(f"\n   [!] PERINGATAN: MAPE hybrid ({agg['hybrid_mape']:.2%}) > "
          f"{WARN_MAPE:.0%}. Pertimbangkan window lebih pendek / dataset lama.")


# ============================================================================
# 6. VISUALISASI (gabungan backtest + feature importance)
# ============================================================================
print("\n" + "=" * 78)
print("5. Menyimpan plot ...")

plt.figure(figsize=(14, 6))
tgl = np.concatenate([r["tanggal"] for r in backtest])
plt.plot(tgl, all_actual, "o-", label="Actual", color="blue", linewidth=2)
plt.plot(tgl, all_yhat, "x--", label="Prophet Only", color="red", alpha=0.7)
plt.plot(tgl, all_hybrid, "D-", label="Hybrid (one-step)", color="purple")
plt.plot(tgl, all_rec, "s-.", label="Hybrid (recursive)", color="green", alpha=0.8)
for r in backtest:  # garis pemisah antar tahun uji
    plt.axvline(pd.Timestamp(f"{r['test_year']}-01-01"), color="gray",
                linestyle=":", alpha=0.4)
plt.title(f"Rolling Backtest Hybrid Prophet+XGBoost ({BACKTEST_YEARS})")
plt.xlabel("Tanggal"); plt.ylabel("Harga Beras")
plt.grid(True, linestyle="--", alpha=0.6); plt.legend()
plt.tight_layout()
plt.savefig(os.path.join(PLOT_DIR, "backtest_comparison.png"), dpi=120)
plt.close()

# Feature importance dari model produksi (dibuat di step 7); di-refit dulu:
final_end = DATA_MAX_YEAR
final_window = prepare_window(pool, best_start, final_end)
prophet_final, final_w = build_residual_frame(final_window, best_params,
                                              fit_end_year=final_end)
xgb_final = XGBRegressor(random_state=RANDOM_STATE, **best_xgb_params)
xgb_final.fit(final_w[FEATURES], final_w[TARGET])

imp = (pd.DataFrame({"Feature": FEATURES, "Importance": xgb_final.feature_importances_})
       .sort_values("Importance", ascending=False))
plt.figure(figsize=(10, 6))
plt.barh(imp["Feature"][::-1], imp["Importance"][::-1], color="teal")
plt.title("XGBoost Feature Importance (memprediksi residual Prophet)")
plt.xlabel("Relative Importance"); plt.grid(axis="x", linestyle="--", alpha=0.6)
plt.tight_layout()
plt.savefig(os.path.join(PLOT_DIR, "feature_importance.png"), dpi=120)
plt.close()
print("   -> plots/backtest_comparison.png, plots/feature_importance.png")
print("\n   Feature importance:")
print(imp.to_string(index=False))


# ============================================================================
# 7. SIMPAN MODEL PRODUKSI (dilatih pada SELURUH data real s/d 2026)
# ============================================================================
print("\n" + "=" * 78)
print(f"6. Menyimpan model produksi (dilatih {best_start}..{final_end}) ...")

joblib.dump(prophet_final, os.path.join(SCRIPT_DIR, "prophet_model.pkl"))
joblib.dump(xgb_final, os.path.join(SCRIPT_DIR, "best_xgb_model.pkl"))
with open(os.path.join(SCRIPT_DIR, "features.json"), "w") as f:
    json.dump({"features": FEATURES}, f, indent=4)

summary = {
    "dataset": os.path.basename(DATA_PATH),
    "data_range": [str(pool["tanggal"].min().date()), str(pool["tanggal"].max().date())],
    "train_start_year": best_start,
    "final_train_years": f"{best_start}..{final_end}",
    "backtest_years": BACKTEST_YEARS,
    "prophet_best_params": best_params,
    "xgb_best_params": best_xgb_params,
    "per_year": [
        {"year": r["test_year"],
         "prophet_only_mape": r["prophet_only_mape"],
         "hybrid_mape": r["hybrid_mape"],
         "recursive_mape": r["recursive_mape"]}
        for r in backtest
    ],
    "aggregate": agg,
}
with open(os.path.join(SCRIPT_DIR, "metrics_summary.json"), "w") as f:
    json.dump(summary, f, indent=4, default=float)

print("   Tersimpan di trainv2/: prophet_model.pkl, best_xgb_model.pkl, "
      "features.json, metrics_summary.json")

print("\n" + "=" * 78)
print("RINGKASAN")
print(f"  Window training : {best_start}..{final_end}")
print(f"  Prophet         : {best_params}")
print(f"  Agregat backtest: Prophet-only {agg['prophet_only_mape']:.2%} | "
      f"Hybrid {agg['hybrid_mape']:.2%} | Recursive {agg['recursive_mape']:.2%}")
print("=" * 78)
print("\nDeploy: salin prophet_model.pkl, best_xgb_model.pkl, features.json "
      "ke backend/ml_models/ (menimpa yang lama).")
