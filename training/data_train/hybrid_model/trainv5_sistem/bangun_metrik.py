"""
Metrik uji sistem "Beras": hasil walk-forward 1 sampai 6 bulan (Januari 2024 sampai Mei 2026) per jenis dan model.
Dibangun dari uji_horizon_*.csv (kode penelitian), bukan diketik tangan.

Keluaran: backend/data/metrik_beras.json
"""
import os, json, sys
import pandas as pd
sys.stdout.reconfigure(encoding="utf-8")
ROOT = r"D:\NGODING\skripsi-prediksi-beras\skripsi-beras"
H = os.path.join(ROOT, "training", "data_train", "hybrid_model", "trainv4_pembanding")
JENIS = ["Bawah I", "Bawah II", "Medium I", "Medium II", "Super I", "Super II"]
MODEL = {"Naive": "naive", "ARIMA(1,1,0)": "arima", "Prophet": "prophet", "Hybrid recursive": "hybrid"}
out = {"protokol": "walk-forward, expanding window, refit tiap bulan; uji target Januari 2024 sampai Mei 2026; "
                   "tanpa faktor eksternal; hyperparameter dibekukan dari trainv3",
       "metrik": {}}
for j in JENIS:
    tag = j.replace(" ", "_") + ("_bulanan" if j == "Medium II" else "")
    df = pd.read_csv(os.path.join(H, f"uji_horizon_{tag}.csv"))
    rows = []
    for _, r in df.iterrows():
        for nama, kode in MODEL.items():
            rows.append({"horizon": int(r["h"]), "model": kode, "n_uji": int(r["n_uji"]),
                         "mape": round(float(r[nama + " MAPE%"]), 3), "mae": round(float(r[nama + " MAE"]), 1),
                         "rmse": round(float(r[nama + " RMSE"]), 1)})
    out["metrik"][j] = rows
p = os.path.join(ROOT, "backend", "data", "metrik_beras.json")
json.dump(out, open(p, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
print("tersimpan:", p, "| jenis:", len(out["metrik"]), "| baris per jenis:", len(out["metrik"]["Medium II"]))
print([x for x in out["metrik"]["Medium II"] if x["horizon"] == 1])
