"""
============================================================================
 LATIH MODEL FINAL SISTEM "BERAS" -- hybrid per jenis (skema realistis)
============================================================================
Satu model hybrid per jenis beras PIHPS DIY (6 jenis):
    harga(T+1) = Prophet(tren + musiman tahunan)  +  XGBoost(residual)
Tanpa faktor eksternal dan tanpa penanda Lebaran (ablasi 23 Okt 2026: Lebaran tidak meningkatkan akurasi).
Hyperparameter dibekukan dari trainv3_realistic/final_config.json (dituning pada
Medium II, tidak dituning ulang per jenis, supaya tidak ada kebocoran).

Artefak (backend/ml_models/beras/):
    <slug>/prophet.pkl, <slug>/xgb.pkl     satu pasang per jenis
    config.json                             fitur, koefisien AR(1) pada selisih (ARIMA(1,1,0)),
                                            rentang data

Pembanding sistem (tidak butuh pustaka tambahan di backend):
    naive         : harga bulan terakhir dipertahankan
    ARIMA(1,1,0)  : koefisien phi dari kuadrat terkecil bersyarat pada selisih harga

Mode uji kesetaraan (CUTOFF=YYYY-MM): melatih hanya sampai bulan itu dan menulis ke
folder sementara, untuk dibandingkan dengan uji_horizon_*_prediksi.csv.

Jalankan dari root repo dengan venv backend (versi paket sama dengan produksi):
    backend/.venv/Scripts/python.exe training/data_train/hybrid_model/trainv5_sistem/train_final_beras.py
============================================================================
"""
import os, sys, json, shutil, logging, warnings
import numpy as np
import pandas as pd
import joblib
from prophet import Prophet
from xgboost import XGBRegressor

warnings.filterwarnings("ignore")
logging.getLogger("cmdstanpy").setLevel(logging.ERROR)
logging.getLogger("prophet").setLevel(logging.ERROR)
sys.stdout.reconfigure(encoding="utf-8")

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
BUL = os.path.join(ROOT, "training", "data_train", "datasets", "data_app", "datav2", "beras",
                   "pihps_6jenis_diy_bulanan_2021-2026.csv")
CFG3 = os.path.join(ROOT, "training", "data_train", "hybrid_model", "trainv3_realistic", "final_config.json")
CUTOFF = os.environ.get("CUTOFF")
OUT = (os.path.join(HERE, "_uji_kesetaraan") if CUTOFF else os.path.join(ROOT, "backend", "ml_models", "beras"))

JENIS = ["Bawah I", "Bawah II", "Medium I", "Medium II", "Super I", "Super II"]
KEYS = ["resid_lag1", "resid_lag2", "price_t", "price_t1", "price_t2", "rolling_mean_3", "diff_t",
        "month_sin", "month_cos"]


def slug(j):
    return j.lower().replace(" ", "-")


def feats_row(prices, resid, date):
    p = list(prices)
    return {"resid_lag1": resid[-1], "resid_lag2": resid[-2], "price_t": p[-1], "price_t1": p[-2], "price_t2": p[-3],
            "rolling_mean_3": float(np.mean(p[-3:])), "diff_t": p[-1] - p[-2],
            "month_sin": float(np.sin(2 * np.pi * date.month / 12)), "month_cos": float(np.cos(2 * np.pi * date.month / 12))}


def phi_cls(series):
    d = np.diff(np.asarray(series, float))
    return float(np.sum(d[1:] * d[:-1]) / np.sum(d[:-1] ** 2))


cfg3 = json.load(open(CFG3, encoding="utf-8"))
PC, XC = cfg3["prophet_tuned"], cfg3["hybrid_xgboost_tuned"]
XP = {k: v for k, v in XC.items() if k not in ("use_exog", "target_mode")}

bul = pd.read_csv(BUL, index_col=0)
bul.index = pd.to_datetime(bul.index + "-01")
if CUTOFF:
    bul = bul.loc[:pd.Timestamp(CUTOFF + "-01")]
if os.path.exists(OUT):
    shutil.rmtree(OUT)
os.makedirs(OUT)

info = {"jenis": {}, "fitur_xgb": KEYS,
        "prophet": PC, "xgb": XP, "metode_phi": "kuadrat terkecil bersyarat pada selisih harga",
        "data_awal": str(bul.index.min().date()), "data_akhir": str(bul.index.max().date()),
        "jumlah_bulan": int(len(bul)), "cutoff": CUTOFF}
for j in JENIS:
    s = bul[j].astype(float)
    m = Prophet(yearly_seasonality=int(PC["yearly_order"]), weekly_seasonality=False, daily_seasonality=False,
                changepoint_prior_scale=PC["changepoint_prior_scale"], seasonality_prior_scale=PC["seasonality_prior_scale"],
                seasonality_mode=PC["seasonality_mode"])
    train = pd.DataFrame({"ds": s.index, "y": s.values})
    m.fit(train)
    in_s = m.predict(train[["ds"]])["yhat"].values
    resid = list(s.values - in_s)
    rows, ys = [], []
    for i in range(3, len(s)):
        rows.append(feats_row(s.values[:i], resid[:i], s.index[i])); ys.append(resid[i])
    xg = XGBRegressor(random_state=42, n_jobs=1, **XP).fit(pd.DataFrame(rows)[KEYS], ys)
    d = os.path.join(OUT, slug(j)); os.makedirs(d)
    joblib.dump(m, os.path.join(d, "prophet.pkl")); joblib.dump(xg, os.path.join(d, "xgb.pkl"))
    info["jenis"][j] = {"slug": slug(j), "phi": phi_cls(s.values), "harga_terakhir": float(s.iloc[-1]),
                        "bulan_terakhir": str(s.index[-1].date())}
    print(f"{j:10s} phi={info['jenis'][j]['phi']:+.4f}  harga terakhir Rp{s.iloc[-1]:,.0f}  ({s.index[-1].date()})")
json.dump(info, open(os.path.join(OUT, "config.json"), "w", encoding="utf-8"), indent=2, ensure_ascii=False)
print("tersimpan di:", OUT)
