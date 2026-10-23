"""
Uji horizon 1 sampai 6 bulan (protokol walk-forward, tanpa faktor eksternal masa depan).

Pertanyaan: pada horizon berapa model masih lebih baik dari naive (harga terakhir dipertahankan)?
Pembimbing (23 Oktober 2026): prediksi jauh perlu histori cukup, dan model harus dibandingkan dengan teknik tradisional.

Setiap origin O (bulan terakhir yang diketahui) diuji pada target O+h, h = 1..6.
  - Latih memakai data sampai O saja (expanding window), refit tiap origin.
  - Uji: origin dari 2023-12 sampai 2025-12 supaya target O+6 masih <= 2026-06? Dipakai aturan:
        target <= 2026-05 (data terakhir). Jumlah titik uji bervariasi per horizon.
  - Pemilihan hyperparameter: tidak ada tuning di sini. Konfigurasi dibekukan dari trainv3 (bukan dituning
    ulang pada data uji), supaya tidak ada kebocoran. Orde ARIMA dibekukan (1,1,0) dari validasi 2023 trainv4.

Model:
  Naive            : harga O untuk semua h
  ARIMA(1,1,0)     : ramal h langkah langsung dari model terlatih sampai O
  Prophet          : konfigurasi tuned trainv3 (tanpa faktor eksternal, regressor lebaran saja), ramal h langkah
  Hybrid recursive : Prophet + XGBoost residual (konfigurasi tuned trainv3), diramal rekursif tiap bulan

Sumber seri harga: kolom harga_beras pada trainv2/harga_beras_2018_2026.csv (Medium II, rata-rata bulanan),
atau berkas bulanan 6 jenis bila argumen jenis diberikan.

Pakai:  python uji_horizon.py            -> Medium II dari dataset skripsi
        python uji_horizon.py "Super I"  -> jenis lain dari pihps_6jenis_diy_bulanan_2021-2026.csv
"""
import os, sys, json, warnings, logging
import numpy as np, pandas as pd
from statsmodels.tsa.arima.model import ARIMA
from prophet import Prophet
from xgboost import XGBRegressor
from joblib import Parallel, delayed

warnings.filterwarnings("ignore")
logging.getLogger("cmdstanpy").setLevel(logging.ERROR); logging.getLogger("prophet").setLevel(logging.ERROR)
sys.stdout.reconfigure(encoding="utf-8")

HERE = os.path.dirname(os.path.abspath(__file__))
V2 = os.path.join(HERE, "..", "trainv2", "harga_beras_2018_2026.csv")
BUL6 = os.path.join(HERE, "..", "..", "datasets", "data_app", "datav2", "beras", "pihps_6jenis_diy_bulanan_2021-2026.csv")
CFG = json.load(open(os.path.join(HERE, "..", "trainv3_realistic", "final_config.json"), encoding="utf-8"))
JENIS = sys.argv[1] if len(sys.argv) > 1 else "Medium II"
H_MAX = 6
START = pd.Timestamp("2020-12-01")  # sama dengan trainv3: target mulai 2021-01, fitur lag Des 2020
FIRST_ORIGIN, LAST_DATA = pd.Timestamp("2023-12-01"), pd.Timestamp("2026-05-01")

SEMUA_BULANAN = os.environ.get("BULANAN_SEMUA") == "1"   # 1 = semua jenis (termasuk Medium II) dari berkas bulanan baru
if JENIS == "Medium II" and not SEMUA_BULANAN:
    raw = pd.read_csv(V2); raw["tanggal"] = pd.to_datetime(raw["tanggal"])
    s = raw.set_index("tanggal")["harga_beras"].astype(float)
    leb = raw.set_index("tanggal")["lebaran"].astype(float)
else:
    b = pd.read_csv(BUL6, index_col=0); b.index = pd.to_datetime(b.index + "-01")
    s = b[JENIS].astype(float)
    raw0 = pd.read_csv(V2); raw0["tanggal"] = pd.to_datetime(raw0["tanggal"])
    leb = raw0.set_index("tanggal")["lebaran"].astype(float)
s = s.asfreq("MS").interpolate(limit_direction="both")  # bulan kosong terisi interpolasi linear (dicatat)
s = s.loc[START:]
leb = leb.reindex(s.index).fillna(0)

PC = CFG["prophet_tuned"]; XC = CFG["hybrid_xgboost_tuned"]


def fit_prophet(train):
    m = Prophet(yearly_seasonality=int(PC["yearly_order"]), weekly_seasonality=False, daily_seasonality=False,
                changepoint_prior_scale=PC["changepoint_prior_scale"], seasonality_prior_scale=PC["seasonality_prior_scale"],
                seasonality_mode=PC["seasonality_mode"])
    m.add_regressor("lebaran")
    m.fit(train[["ds", "y", "lebaran"]])
    return m


def feats_row(prices, resid, date):
    """Fitur hybrid untuk memprediksi bulan 'date' dari riwayat prices (sampai bulan sebelumnya) dan resid."""
    p = list(prices)
    return {"resid_lag1": resid[-1], "resid_lag2": resid[-2], "price_t": p[-1], "price_t1": p[-2], "price_t2": p[-3],
            "rolling_mean_3": float(np.mean(p[-3:])), "diff_t": p[-1] - p[-2],
            "month_sin": np.sin(2 * np.pi * date.month / 12), "month_cos": np.cos(2 * np.pi * date.month / 12),
            "lebaran_next": float(leb.get(date, 0.0))}


def satu_origin(O):
    hist = s.loc[:O]
    train = pd.DataFrame({"ds": hist.index, "y": hist.values, "lebaran": leb.loc[:O].values})
    out = {"origin": O}
    targets = [O + pd.DateOffset(months=h) for h in range(1, H_MAX + 1)]
    targets = [t for t in targets]
    # naive
    for h, t in enumerate(targets, 1):
        out[f"Naive|{h}"] = float(hist.iloc[-1])
    # ARIMA(1,1,0)
    try:
        f = ARIMA(hist, order=(1, 1, 0), trend="n").fit().forecast(H_MAX).values
    except Exception:
        f = np.repeat(hist.iloc[-1], H_MAX)
    for h in range(1, H_MAX + 1):
        out[f"ARIMA(1,1,0)|{h}"] = float(f[h - 1])
    # Prophet + Hybrid
    m = fit_prophet(train)
    fut = pd.DataFrame({"ds": list(hist.index) + targets, "lebaran": list(leb.loc[:O].values) + [float(leb.get(t, 0.0)) for t in targets]})
    yhat_all = m.predict(fut)["yhat"].values
    in_s, fut_s = yhat_all[:len(hist)], yhat_all[len(hist):]
    for h in range(1, H_MAX + 1):
        out[f"Prophet|{h}"] = float(fut_s[h - 1])
    # XGBoost residual dilatih pada (resid_lag, price lag) dari riwayat sampai O
    resid = list(hist.values - in_s)
    rows, ys = [], []
    for i in range(3, len(hist)):
        d = hist.index[i]
        rows.append(feats_row(hist.values[:i], resid[:i], d)); ys.append(resid[i])
    keys = ["resid_lag1", "resid_lag2", "price_t", "price_t1", "price_t2", "rolling_mean_3", "diff_t", "month_sin", "month_cos", "lebaran_next"]
    Xtr = pd.DataFrame(rows)[keys]
    xp = {k: v for k, v in XC.items() if k not in ("use_exog", "target_mode")}
    xg = XGBRegressor(random_state=42, n_jobs=1, **xp).fit(Xtr, ys)
    prices, res = list(hist.values), list(resid)
    for h, t in enumerate(targets, 1):
        r_hat = float(xg.predict(pd.DataFrame([feats_row(prices, res, t)])[keys])[0])
        y_hat = float(fut_s[h - 1] + r_hat)
        out[f"Hybrid recursive|{h}"] = y_hat
        res.append(r_hat)  # residual masa depan tidak diketahui: diisi koreksi terprediksi
        prices.append(y_hat)
    return out


origins = [o for o in pd.date_range(FIRST_ORIGIN, LAST_DATA - pd.DateOffset(months=1), freq="MS")]
rows = Parallel(n_jobs=max(1, (os.cpu_count() or 2) - 1))(delayed(satu_origin)(o) for o in origins)
df = pd.DataFrame(rows)

models = ["Naive", "ARIMA(1,1,0)", "Prophet", "Hybrid recursive"]
res = []
for h in range(1, H_MAX + 1):
    pts = [(o, o + pd.DateOffset(months=h)) for o in origins if o + pd.DateOffset(months=h) <= LAST_DATA]
    y = np.array([s.loc[t] for _, t in pts])
    row = {"h": h, "n_uji": len(pts)}
    for m in models:
        p = np.array([df.loc[df.origin == o, f"{m}|{h}"].values[0] for o, _ in pts])
        row[m + " MAPE%"] = round(float(np.mean(np.abs(y - p) / y) * 100), 3)
        row[m + " MAE"] = round(float(np.mean(np.abs(y - p))), 1)
        row[m + " RMSE"] = round(float(np.sqrt(np.mean((y - p) ** 2))), 1)
    res.append(row)
r = pd.DataFrame(res)
tag = JENIS.replace(" ", "_") + ("_bulanan" if (SEMUA_BULANAN and JENIS == "Medium II") else "")
r.to_csv(os.path.join(HERE, f"uji_horizon_{tag}.csv"), index=False)
df.to_csv(os.path.join(HERE, f"uji_horizon_{tag}_prediksi.csv"), index=False)
print(f"Jenis: {JENIS} | origin {origins[0].date()} .. {origins[-1].date()} | bulan interpolasi: ", int(pd.Series(s).isna().sum()))
print(r[["h", "n_uji"] + [m + " MAPE%" for m in models]].to_string(index=False))
print()
print(r[["h"] + [m + " MAE" for m in models]].to_string(index=False))
