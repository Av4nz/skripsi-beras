"""
============================================================================
 EVALUASI METRIK UNTUK SKRIPSI (BAB IV)  -- trainv2
============================================================================
Menghasilkan TABEL PERBANDINGAN 3 model dengan split kronologis tunggal yang
mudah dilaporkan di skripsi:

        Latih : Januari 2021 -- Desember 2024
        Uji   : Januari 2025 -- Desember 2025   (12 bulan penuh)

Tiga model dibandingkan (menjawab: mengapa memilih hybrid):

    1. Prophet-only        -> trend + yearly seasonality + regressor lebaran
    2. XGBoost-only        -> murni machine learning, memprediksi harga_beras
                              langsung dari fitur (lag/rolling/eksogen/musiman),
                              TANPA komponen Prophet
    3. Hybrid (Prophet+XGBoost) -> harga = Prophet + XGBoost(residual Prophet)

Untuk tiap model dilaporkan MAE, RMSE, MAPE. Untuk model yang bergantung pada
nilai masa lalu (XGBoost-only & Hybrid) dilaporkan DUA skenario:
    - one-step   : fitur lag memakai nilai AKTUAL bulan sebelumnya
                   (evaluasi akurasi 1 langkah ke depan / headline accuracy)
    - recursive  : fitur lag memakai PREDIKSI model sendiri
                   (evaluasi prakiraan banyak bulan ke depan / horizon panjang)

Konfigurasi (Prophet & XGBoost) DIBEKUKAN dari hasil training terakhir
(metrics_summary.json) supaya tabel konsisten dengan model yang di-deploy.
Model final untuk deployment tetap dilatih pada SELURUH data 2021..2026 oleh
train_hybrid.py -- skrip INI hanya menghasilkan angka evaluasi untuk laporan.

Output:
    - tabel ke konsol
    - thesis_metrics.json          (angka mentah, machine-readable)
    - thesis_metrics_table.md      (tabel Markdown siap tempel ke BAB IV)

Jalankan (dari root repo) dengan interpreter venv backend:
    backend/.venv/Scripts/python.exe \
        backend/data_train/hybrid_model/trainv2/evaluate_thesis_metrics.py
============================================================================
"""

import os
import json
import logging
import warnings

import numpy as np
import pandas as pd

from prophet import Prophet
from sklearn.metrics import (
    mean_absolute_error,
    mean_absolute_percentage_error,
    root_mean_squared_error,
)
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

RANDOM_STATE = 42

# Split kronologis tunggal (thesis-aligned).
TRAIN_START_YEAR = 2021          # 2018-2020 rezim harga lama -> tidak dipakai
TEST_YEAR = 2025                 # 12 bulan penuh sebagai data uji

# Fitur hybrid (11) -- identik dengan backend/ml_models/features.json.
FEATURES_HYBRID = [
    "harga_gkg", "curah_hujan", "produksi_padi", "inflasi_pangan",
    "lag_1", "lag_2", "rolling_mean_3",
    "residual_lag_1", "residual_lag_2", "month_sin", "month_cos",
]
# Fitur XGBoost-only: sama, tetapi TANPA fitur turunan-Prophet (residual_lag).
FEATURES_XGB_ONLY = [
    "harga_gkg", "curah_hujan", "produksi_padi", "inflasi_pangan",
    "lag_1", "lag_2", "rolling_mean_3", "month_sin", "month_cos",
]

# Parameter dibekukan dari metrics_summary.json (hasil tuning train_hybrid.py).
_SUMMARY_PATH = os.path.join(SCRIPT_DIR, "metrics_summary.json")
if os.path.exists(_SUMMARY_PATH):
    with open(_SUMMARY_PATH) as f:
        _s = json.load(f)
    PROPHET_PARAMS = _s["prophet_best_params"]
    XGB_PARAMS = _s["xgb_best_params"]
else:  # fallback bila summary belum ada
    PROPHET_PARAMS = {"changepoint_prior_scale": 0.5,
                      "seasonality_prior_scale": 10.0,
                      "seasonality_mode": "multiplicative"}
    XGB_PARAMS = dict(subsample=0.7, reg_lambda=5.0, reg_alpha=0, n_estimators=30,
                      min_child_weight=7, max_depth=4, learning_rate=0.1,
                      gamma=1.0, colsample_bytree=1.0)


def metrics(y_true, y_pred):
    return {
        "MAE": float(mean_absolute_error(y_true, y_pred)),
        "RMSE": float(root_mean_squared_error(y_true, y_pred)),
        "MAPE": float(mean_absolute_percentage_error(y_true, y_pred)),
    }


# ============================================================================
# 1. HELPERS
# ============================================================================
def add_base_features(frame):
    frame = frame.copy()
    frame["lag_1"] = frame["harga_beras"].shift(1)
    frame["lag_2"] = frame["harga_beras"].shift(2)
    frame["rolling_mean_3"] = frame["harga_beras"].shift(1).rolling(3).mean()
    month = frame["tanggal"].dt.month
    frame["month_sin"] = np.sin(2 * np.pi * month / 12)
    frame["month_cos"] = np.cos(2 * np.pi * month / 12)
    return frame


def fit_prophet(train_frame):
    m = Prophet(
        yearly_seasonality=True, weekly_seasonality=False, daily_seasonality=False,
        changepoint_prior_scale=PROPHET_PARAMS["changepoint_prior_scale"],
        seasonality_prior_scale=PROPHET_PARAMS["seasonality_prior_scale"],
        seasonality_mode=PROPHET_PARAMS["seasonality_mode"],
    )
    m.add_regressor("lebaran")
    p = train_frame[["tanggal", "harga_beras", "lebaran"]].rename(
        columns={"tanggal": "ds", "harga_beras": "y"})
    m.fit(p)
    return m


def prophet_predict(model, frame):
    p = frame[["tanggal", "lebaran"]].rename(columns={"tanggal": "ds"})
    return model.predict(p)["yhat"].values


# ============================================================================
# 2. LOAD & SPLIT
# ============================================================================
print("=" * 78)
print("EVALUASI METRIK SKRIPSI (split kronologis tunggal)")
print("=" * 78)
pool = pd.read_csv(DATA_PATH)
pool["tanggal"] = pd.to_datetime(pool["tanggal"])
pool = pool.sort_values("tanggal").reset_index(drop=True)

# Buang rezim harga lama 2018-2020, tambahkan fitur, buang NaN awal.
full = pool[pool["tanggal"].dt.year >= TRAIN_START_YEAR].copy()
full = add_base_features(full)
full = full.dropna(subset=["lag_1", "lag_2", "rolling_mean_3"]).reset_index(drop=True)

train = full[full["tanggal"].dt.year < TEST_YEAR].reset_index(drop=True)
test = full[full["tanggal"].dt.year == TEST_YEAR].reset_index(drop=True)

print(f"Dataset        : {os.path.basename(DATA_PATH)} "
      f"({pool['tanggal'].min().date()}..{pool['tanggal'].max().date()})")
print(f"Window dipakai : {TRAIN_START_YEAR}.. (2018-2020 dibuang: rezim harga lama)")
print(f"Latih          : {train['tanggal'].min().date()} .. "
      f"{train['tanggal'].max().date()}  ({len(train)} bulan)")
print(f"Uji            : {test['tanggal'].min().date()} .. "
      f"{test['tanggal'].max().date()}  ({len(test)} bulan)")
print(f"Prophet params : {PROPHET_PARAMS}")
print(f"XGBoost params : {XGB_PARAMS}")

y_test = test["harga_beras"].values
results = {}

# ============================================================================
# 3. MODEL 1 -- PROPHET-ONLY
# ============================================================================
prophet = fit_prophet(train)
yhat_test = prophet_predict(prophet, test)
results["Prophet-only"] = {"one_step": metrics(y_test, yhat_test)}

# residual pada train+test (dipakai model hybrid)
full["yhat"] = prophet_predict(prophet, full)
full["residual"] = full["harga_beras"] - full["yhat"]
full["residual_lag_1"] = full["residual"].shift(1)
full["residual_lag_2"] = full["residual"].shift(2)
full_h = full.dropna(subset=["residual_lag_1", "residual_lag_2"]).reset_index(drop=True)
train_h = full_h[full_h["tanggal"].dt.year < TEST_YEAR].reset_index(drop=True)
test_h = full_h[full_h["tanggal"].dt.year == TEST_YEAR].reset_index(drop=True)
y_test_h = test_h["harga_beras"].values

# ============================================================================
# 4. MODEL 2 -- XGBOOST-ONLY (murni ML, prediksi harga langsung)
# ============================================================================
xgb_only = XGBRegressor(random_state=RANDOM_STATE, **XGB_PARAMS)
xgb_only.fit(train[FEATURES_XGB_ONLY], train["harga_beras"])

# one-step: lag = nilai aktual
xgb_only_onestep = xgb_only.predict(test[FEATURES_XGB_ONLY])

# recursive: lag = prediksi sendiri
def recursive_direct(model, feats, train_df, test_df):
    hist = list(train_df["harga_beras"].values)
    preds = []
    for i in range(len(test_df)):
        row = test_df.iloc[[i]].copy()
        row["lag_1"] = hist[-1]
        row["lag_2"] = hist[-2]
        row["rolling_mean_3"] = np.mean(hist[-3:])
        p = float(model.predict(row[feats])[0])
        preds.append(p)
        hist.append(p)
    return np.array(preds)

xgb_only_recursive = recursive_direct(xgb_only, FEATURES_XGB_ONLY, train, test)
results["XGBoost-only"] = {
    "one_step": metrics(y_test, xgb_only_onestep),
    "recursive": metrics(y_test, xgb_only_recursive),
}

# ============================================================================
# 5. MODEL 3 -- HYBRID (Prophet + XGBoost residual)
# ============================================================================
xgb_res = XGBRegressor(random_state=RANDOM_STATE, **XGB_PARAMS)
xgb_res.fit(train_h[FEATURES_HYBRID], train_h["residual"])

# one-step: residual_lag & harga_lag = aktual
hybrid_onestep = test_h["yhat"].values + xgb_res.predict(test_h[FEATURES_HYBRID])

# recursive: lag harga & residual = prediksi sendiri
def recursive_hybrid(model, train_df, test_df):
    hp = list(train_df["harga_beras"].values)
    hr = list(train_df["residual"].values)
    preds = []
    for i in range(len(test_df)):
        row = test_df.iloc[[i]].copy()
        row["lag_1"] = hp[-1]
        row["lag_2"] = hp[-2]
        row["rolling_mean_3"] = np.mean(hp[-3:])
        row["residual_lag_1"] = hr[-1]
        row["residual_lag_2"] = hr[-2]
        pr = float(model.predict(row[FEATURES_HYBRID])[0])
        yv = float(row["yhat"].values[0])
        pp = yv + pr
        preds.append(pp)
        hp.append(pp)
        hr.append(pr)
    return np.array(preds)

hybrid_recursive = recursive_hybrid(xgb_res, train_h, test_h)
results["Hybrid (Prophet+XGBoost)"] = {
    "one_step": metrics(y_test_h, hybrid_onestep),
    "recursive": metrics(y_test_h, hybrid_recursive),
}

# ============================================================================
# 6. TABEL KONSOL
# ============================================================================
def fmt(m):
    return f"{m['MAE']:>10.1f} {m['RMSE']:>10.1f} {m['MAPE']:>9.2%}"

print("\n" + "=" * 78)
print(f"TABEL PERBANDINGAN  (uji: {TEST_YEAR}, {len(test)} bulan)")
print("=" * 78)
print(f"{'Model':<34}{'skenario':<11}{'MAE':>10}{'RMSE':>11}{'MAPE':>10}")
print("-" * 78)
order = ["Prophet-only", "XGBoost-only", "Hybrid (Prophet+XGBoost)"]
for name in order:
    r = results[name]
    print(f"{name:<34}{'one-step':<11}{fmt(r['one_step'])}")
    if "recursive" in r:
        print(f"{'':<34}{'recursive':<11}{fmt(r['recursive'])}")
print("-" * 78)
print("one-step  = akurasi prakiraan 1 bulan ke depan (fitur lag pakai nilai aktual)")
print("recursive = prakiraan banyak bulan (fitur lag pakai prediksi model sendiri)")

# ============================================================================
# 7. SIMPAN JSON + TABEL MARKDOWN
# ============================================================================
out = {
    "dataset": os.path.basename(DATA_PATH),
    "train_period": [str(train["tanggal"].min().date()),
                     str(train["tanggal"].max().date())],
    "test_period": [str(test["tanggal"].min().date()),
                    str(test["tanggal"].max().date())],
    "train_start_year": TRAIN_START_YEAR,
    "test_year": TEST_YEAR,
    "note_2018_2020": "dibuang dari pemodelan (rezim harga lama ~11rb)",
    "prophet_params": PROPHET_PARAMS,
    "xgb_params": XGB_PARAMS,
    "results": results,
}
with open(os.path.join(SCRIPT_DIR, "thesis_metrics.json"), "w") as f:
    json.dump(out, f, indent=4)

# Tabel Markdown headline (one-step) -- untuk narasi utama BAB IV.
def md_row(name, m):
    return f"| {name} | {m['MAE']:.1f} | {m['RMSE']:.1f} | {m['MAPE']*100:.2f}% |"

lines = []
lines.append(f"**Tabel Perbandingan Kinerja Model** "
             f"(data latih {train['tanggal'].min().date()}"
             f"–{train['tanggal'].max().date()}, "
             f"data uji {test['tanggal'].min().date()}"
             f"–{test['tanggal'].max().date()}, prakiraan 1 bulan ke depan)\n")
lines.append("| Model | MAE (Rp) | RMSE (Rp) | MAPE |")
lines.append("|---|---|---|---|")
for name in order:
    lines.append(md_row(name, results[name]["one_step"]))
lines.append("")
lines.append("**Kinerja pada prakiraan banyak bulan ke depan (recursive)**\n")
lines.append("| Model | MAE (Rp) | RMSE (Rp) | MAPE |")
lines.append("|---|---|---|---|")
for name in order:
    r = results[name]
    scenario = r.get("recursive", r["one_step"])
    tag = name if "recursive" in r else f"{name} (tanpa lag, sama sprt one-step)"
    lines.append(md_row(tag, scenario))
md_text = "\n".join(lines) + "\n"
with open(os.path.join(SCRIPT_DIR, "thesis_metrics_table.md"), "w",
          encoding="utf-8") as f:
    f.write(md_text)

print("\nTersimpan: thesis_metrics.json, thesis_metrics_table.md")
print("=" * 78)
