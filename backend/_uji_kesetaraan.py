"""
Uji kesetaraan: rice_predictor (kode backend baru) harus menghasilkan prediksi yang sama dengan
uji_horizon.py (kode penelitian) bila dilatih pada data yang sama.

Artefak _uji_kesetaraan dilatih sampai Desember 2025. Untuk origin Desember 2025, kode backend
meramal Januari sampai Mei 2026. Bandingkan dengan uji_horizon (yang melatih ulang pada origin yang sama).
"""
import os, sys, logging, warnings
import numpy as np, pandas as pd
warnings.filterwarnings("ignore")
logging.getLogger("cmdstanpy").setLevel(logging.ERROR); logging.getLogger("prophet").setLevel(logging.ERROR)
sys.stdout.reconfigure(encoding="utf-8")

ROOT = r"D:\NGODING\skripsi-prediksi-beras\skripsi-beras"
sys.path.insert(0, os.path.join(ROOT, "backend"))
from app.services import rice_predictor as rp

ART = os.path.join(ROOT, "training", "data_train", "hybrid_model", "trainv5_sistem", "_uji_kesetaraan")
rp.load_rice_models(ART)
bul = pd.read_csv(os.path.join(ROOT, "training", "data_train", "datasets", "data_app", "datav2", "beras",
                               "pihps_6jenis_diy_bulanan_2021-2026.csv"), index_col=0)
bul.index = pd.to_datetime(bul.index + "-01")
hist_all = bul

# bandingkan dengan uji_horizon: origin 2025-12, horizon 1..5 (sampai 2026-05)
H = os.path.join(ROOT, "training", "data_train", "hybrid_model", "trainv4_pembanding")
selisih_maks = 0.0
for jenis in rp.list_rice_types():
    hist = hist_all.loc[:"2025-12-01", jenis]
    res = rp.predict_rice(jenis, hist, 5)
    tag = jenis.replace(" ", "_") + ("_bulanan" if jenis == "Medium II" else "")
    ref = pd.read_csv(os.path.join(H, f"uji_horizon_{tag}_prediksi.csv"), parse_dates=["origin"])
    ref = ref[ref.origin == "2025-12-01"].iloc[0]
    for r in res:
        for nama, val, kolom in (("hybrid", r.hybrid, "Hybrid recursive"), ("prophet", r.prophet, "Prophet"),
                                 ("naive", r.naive, "Naive"), ("arima", r.arima, "ARIMA(1,1,0)")):
            d = abs(val - ref[f"{kolom}|{r.step}"])
            selisih_maks = max(selisih_maks, d)
            if nama == "hybrid" and r.step in (1, 5):
                print(f"{jenis:10s} h={r.step}  backend {val:9.2f}  riset {ref[f'{kolom}|{r.step}']:9.2f}  selisih {d:7.2f}")
print("selisih mutlak terbesar (semua jenis, h1-5, 4 model): Rp", round(selisih_maks, 3))
