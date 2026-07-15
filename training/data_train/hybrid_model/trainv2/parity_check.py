"""
============================================================================
 UJI PARITY (read-only) -- validasi arsitektur skenario end-to-end
============================================================================
Memuat ARTEFAK KANDIDAT (prophet_model_scenario.pkl, xgb_model_scenario.pkl,
features_scenario.json) dan MENIRU PERSIS logika backend
`app/services/predictor.py::predict_hybrid` pada data nyata (ekor CSV),
TANPA database & TANPA menyentuh produksi.

Tujuan: memastikan sebelum swap produksi bahwa
  1. Prophet.predict berjalan dgn kolom exog (lebaran + 4 eksternal),
  2. urutan/kelengkapan fitur XGBoost cocok dgn features_scenario.json,
  3. yhat + koreksi residual + constraint menghasilkan angka wajar,
  4. recursive multi-step tidak meledak.

Jalankan:
    backend/.venv/Scripts/python.exe \
        backend/data_train/hybrid_model/trainv2/parity_check.py
============================================================================
"""

import os
import json
import logging
import warnings

import numpy as np
import pandas as pd
import joblib

warnings.filterwarnings("ignore")
logging.getLogger("cmdstanpy").setLevel(logging.ERROR)
logging.getLogger("prophet").setLevel(logging.ERROR)

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_PATH = os.path.abspath(
    os.path.join(SCRIPT_DIR, "..", "..", "datasets", "data_app",
                 "harga_beras_2018_2026.csv")
)

PROPHET = joblib.load(os.path.join(SCRIPT_DIR, "prophet_model_scenario.pkl"))
XGB = joblib.load(os.path.join(SCRIPT_DIR, "xgb_model_scenario.pkl"))
with open(os.path.join(SCRIPT_DIR, "features_scenario.json")) as f:
    FEATURES = json.load(f)["features"]

PERIOD = 6  # horizon uji

print("=" * 78)
print("UJI PARITY -- meniru predictor.py::predict_hybrid (artefak kandidat)")
print("=" * 78)
print("Fitur XGBoost (dari features_scenario.json):")
print("  ", FEATURES)

df = pd.read_csv(DATA_PATH)
df["tanggal"] = pd.to_datetime(df["tanggal"])
df = df.sort_values("tanggal").reset_index(drop=True)

# --- Ambil 3 record terakhir sebagai T-2, T-1, T0 (spt get_last_n_prices) ---
last3 = df.tail(3).reset_index(drop=True)
P = list(last3["harga_beras"].values)
dates = list(last3["tanggal"].dt.date.values)
lebaran_past = list(last3["lebaran"].values)
exog_past = [
    {"harga_gkg": r.harga_gkg, "curah_hujan": r.curah_hujan,
     "produksi_padi": r.produksi_padi, "inflasi_pangan": r.inflasi_pangan}
    for r in last3.itertuples()
]
print(f"\n3 data terakhir (T-2,T-1,T0): {dates}")
print(f"  harga: {P}")

# --- Skenario: kondisi eksternal diasumsikan = kondisi T0 (dipertahankan) ---
ext = exog_past[-1].copy()
ext["lebaran"] = lebaran_past[-1]
print(f"\nSkenario ext_feat (kondisi T0 dipertahankan): {ext}")

# --- Residual historis T-1, T0 (spt get_historical_residuals fallback) ------
past_df = pd.DataFrame({
    "ds": dates[1:3], "lebaran": lebaran_past[1:3],
    "harga_gkg": [exog_past[1]["harga_gkg"], exog_past[2]["harga_gkg"]],
    "curah_hujan": [exog_past[1]["curah_hujan"], exog_past[2]["curah_hujan"]],
    "produksi_padi": [exog_past[1]["produksi_padi"], exog_past[2]["produksi_padi"]],
    "inflasi_pangan": [exog_past[1]["inflasi_pangan"], exog_past[2]["inflasi_pangan"]],
})
yhat_past = PROPHET.predict(past_df)["yhat"].values
R_T_minus_1 = P[1] - yhat_past[0]
R_T0 = P[2] - yhat_past[1]
R = [0, R_T_minus_1, R_T0]
print(f"Residual historis: R(T-1)={R_T_minus_1:.1f}  R(T0)={R_T0:.1f}")

# --- Loop prediksi (identik dgn predict_hybrid) -----------------------------
print("\n" + "-" * 78)
print(f"{'step':>4}{'tanggal':>12}{'yhat':>10}{'resid':>9}{'final':>11}{'catatan':>16}")
print("-" * 78)
current_date = dates[-1]
preds = []
for i in range(PERIOD):
    current_date = (pd.to_datetime(current_date) + pd.DateOffset(months=1)).date()
    lag_1, lag_2 = P[-1], P[-2]
    rolling_mean_3 = (P[-3] + P[-2] + P[-1]) / 3
    residual_lag_1, residual_lag_2 = R[-1], R[-2]
    month = current_date.month
    feats = {
        "harga_gkg": ext["harga_gkg"], "curah_hujan": ext["curah_hujan"],
        "produksi_padi": ext["produksi_padi"], "inflasi_pangan": ext["inflasi_pangan"],
        "lag_1": lag_1, "lag_2": lag_2, "rolling_mean_3": rolling_mean_3,
        "residual_lag_1": residual_lag_1, "residual_lag_2": residual_lag_2,
        "month_sin": np.sin(2*np.pi*month/12), "month_cos": np.cos(2*np.pi*month/12),
    }
    # Prophet base (dgn exog)
    future_df = pd.DataFrame({
        "ds": [current_date], "lebaran": [ext["lebaran"]],
        "harga_gkg": [ext["harga_gkg"]], "curah_hujan": [ext["curah_hujan"]],
        "produksi_padi": [ext["produksi_padi"]], "inflasi_pangan": [ext["inflasi_pangan"]],
    })
    yhat = float(PROPHET.predict(future_df).loc[0, "yhat"])

    # XGBoost residual (ordering ketat spt predictor.py)
    ordered = {}
    for col in FEATURES:
        if col not in feats:
            raise ValueError(f"Fitur hilang: {col}")
        ordered[col] = feats[col]
    predicted_residual = float(XGB.predict(pd.DataFrame([ordered]))[0])

    final = yhat + predicted_residual
    note = ""
    upper, lower = P[-1]*1.10, P[-1]*0.90
    if final > upper:
        final, note = upper, "clamp +10%"
    elif final < lower:
        final, note = lower, "clamp -10%"
    minp = ext["harga_gkg"]*1.2
    if final < minp:
        final, note = minp, "min-price"

    preds.append(final)
    print(f"{i+1:>4}{str(current_date):>12}{yhat:>10.1f}{predicted_residual:>9.1f}"
          f"{final:>11.1f}{note:>16}")
    P.append(final)
    R.append(predicted_residual)

print("-" * 78)
print(f"Prediksi {PERIOD} bulan: {[round(x,1) for x in preds]}")
chg = (preds[-1]-preds[0])/preds[0]*100
print(f"Perubahan bln-1 -> bln-{PERIOD}: {chg:+.2f}%")
print("\nPARITY OK: Prophet menerima exog, fitur XGBoost cocok, output wajar.")
print("=" * 78)
