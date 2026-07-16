"""
============================================================================
 DIAGNOSTIK RESIDUAL PROPHET  (evidence sebelum feature engineering)
============================================================================
Menjawab satu pertanyaan: "Apakah residual Prophet masih menyimpan pola/
informasi yang layak dipelajari oleh XGBoost?"  -> keputusan hybrid/FE
diambil dari bukti statistik, bukan asumsi.

Yang dihasilkan (plots/residual_diagnostics.png, grid 3x3):
  1. Residual vs waktu
  2. Histogram residual (+ kurva normal)
  3. Rolling std residual (kestabilan varians)
  4. ACF residual (+ pita signifikansi 95%)
  5. PACF residual (+ pita signifikansi 95%)
  6. Ljung-Box p-value per lag (garis ambang 0.05)
  7. QQ-plot (normalitas)
  8. Residual vs fitted (yhat)
  9. Scatter residual aktual vs prediksi XGBoost (out-of-sample, backtest)

Statistik dicetak ke konsol: mean, varians, std, ACF lag-1..6, uji Ljung-Box,
uji normalitas, dan R^2 kemampuan XGBoost memprediksi residual OOS.

ACF/PACF/Ljung-Box diimplementasikan manual (numpy + scipy) -> tidak perlu
statsmodels.
============================================================================
"""
import os, logging, warnings
warnings.filterwarnings("ignore")
logging.getLogger("cmdstanpy").setLevel(logging.ERROR)

import numpy as np
import pandas as pd
from scipy import stats

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from prophet import Prophet
from xgboost import XGBRegressor
from sklearn.metrics import r2_score

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_PATH = os.path.abspath(os.path.join(SCRIPT_DIR, "..", "..", "datasets",
                            "data_app", "harga_beras_2018_2026.csv"))
PLOT_DIR = os.path.join(SCRIPT_DIR, "plots")
os.makedirs(PLOT_DIR, exist_ok=True)

START_YEAR = 2021
DIAG_CPS = 0.05           # Prophet moderat (default) -> kasus di mana residual bermakna
DIAG_MODE = "multiplicative"
SPS = 10.0
FEATURES = ["harga_gkg", "curah_hujan", "produksi_padi", "inflasi_pangan",
            "lag_1", "lag_2", "rolling_mean_3", "residual_lag_1",
            "residual_lag_2", "month_sin", "month_cos"]

# --------------------------------------------------------------------------
# Estimator manual
# --------------------------------------------------------------------------
def acf(x, nlags):
    x = np.asarray(x, float); x = x - x.mean()
    denom = np.sum(x * x)
    return np.array([1.0] + [np.sum(x[k:] * x[:-k]) / denom for k in range(1, nlags + 1)])

def pacf(x, nlags):
    r = acf(x, nlags)
    phi = np.zeros((nlags + 1, nlags + 1))
    out = [1.0]
    phi[1, 1] = r[1]; out.append(r[1])
    for k in range(2, nlags + 1):
        num = r[k] - sum(phi[k - 1, j] * r[k - j] for j in range(1, k))
        den = 1 - sum(phi[k - 1, j] * r[j] for j in range(1, k))
        phi[k, k] = num / den if den != 0 else 0.0
        for j in range(1, k):
            phi[k, j] = phi[k - 1, j] - phi[k, k] * phi[k - 1, k - j]
        out.append(phi[k, k])
    return np.array(out)

def ljung_box(x, lags):
    n = len(x); r = acf(x, max(lags))
    rows = []
    for h in lags:
        Q = n * (n + 2) * sum(r[k] ** 2 / (n - k) for k in range(1, h + 1))
        rows.append((h, Q, float(stats.chi2.sf(Q, h))))
    return rows

# --------------------------------------------------------------------------
# Data & fitur
# --------------------------------------------------------------------------
pool = pd.read_csv(DATA_PATH); pool["tanggal"] = pd.to_datetime(pool["tanggal"])
pool = pool.sort_values("tanggal").reset_index(drop=True)

def add_feats(f):
    f = f.copy()
    f["lag_1"] = f["harga_beras"].shift(1)
    f["lag_2"] = f["harga_beras"].shift(2)
    f["rolling_mean_3"] = f["harga_beras"].shift(1).rolling(3).mean()
    m = f["tanggal"].dt.month
    f["month_sin"] = np.sin(2 * np.pi * m / 12); f["month_cos"] = np.cos(2 * np.pi * m / 12)
    return f

def fit_prophet(train, cps, mode):
    m = Prophet(yearly_seasonality=True, weekly_seasonality=False, daily_seasonality=False,
                changepoint_prior_scale=cps, seasonality_prior_scale=SPS, seasonality_mode=mode)
    m.add_regressor("lebaran")
    m.fit(train[["tanggal", "harga_beras", "lebaran"]].rename(
        columns={"tanggal": "ds", "harga_beras": "y"}))
    return m

def yhat(m, f):
    return m.predict(f[["tanggal", "lebaran"]].rename(columns={"tanggal": "ds"}))["yhat"].values

# In-sample: fit Prophet moderat pada 2021..2025, residual in-sample.
w = add_feats(pool[(pool.tanggal.dt.year >= START_YEAR) & (pool.tanggal.dt.year <= 2025)])
w = w.dropna(subset=["lag_1", "lag_2", "rolling_mean_3"]).reset_index(drop=True)
mp = fit_prophet(w, DIAG_CPS, DIAG_MODE)
w["yhat"] = yhat(mp, w)
w["residual"] = w["harga_beras"] - w["yhat"]
res = w["residual"].values
n = len(res)

# Kontras: varians residual model FLEXIBLE (cps=0.5) in-sample.
mp_flex = fit_prophet(w[["tanggal", "harga_beras", "lebaran"]], 0.5, "multiplicative")
res_flex = w["harga_beras"].values - yhat(mp_flex, w)

# --------------------------------------------------------------------------
# Panel 9: kemampuan XGBoost memprediksi residual OUT-OF-SAMPLE (backtest)
# --------------------------------------------------------------------------
def oos_residual_pred(cps, mode):
    act, pred = [], []
    for ty in [2024, 2025, 2026]:
        ww = add_feats(pool[(pool.tanggal.dt.year >= START_YEAR) & (pool.tanggal.dt.year <= ty)])
        ww = ww.dropna(subset=["lag_1", "lag_2", "rolling_mean_3"]).reset_index(drop=True)
        m = fit_prophet(ww[ww.tanggal.dt.year < ty], cps, mode)
        ww["yhat"] = yhat(m, ww); ww["residual"] = ww["harga_beras"] - ww["yhat"]
        ww["residual_lag_1"] = ww["residual"].shift(1); ww["residual_lag_2"] = ww["residual"].shift(2)
        ww = ww.dropna(subset=["residual_lag_1", "residual_lag_2"]).reset_index(drop=True)
        tr = ww[ww.tanggal.dt.year < ty]; te = ww[ww.tanggal.dt.year == ty]
        x = XGBRegressor(n_estimators=60, learning_rate=0.05, max_depth=3,
                         subsample=0.8, colsample_bytree=0.8, random_state=42)
        x.fit(tr[FEATURES], tr["residual"])
        act += list(te["residual"].values); pred += list(x.predict(te[FEATURES]))
    return np.array(act), np.array(pred)

res_act_oos, res_pred_oos = oos_residual_pred(DIAG_CPS, DIAG_MODE)
r2_oos = r2_score(res_act_oos, res_pred_oos)

# --------------------------------------------------------------------------
# Statistik cetak
# --------------------------------------------------------------------------
NL = 15
acf_v = acf(res, NL); pacf_v = pacf(res, NL)
lb = ljung_box(res, [1, 3, 6, 12])
sh_stat, sh_p = stats.shapiro(res)
band = 1.96 / np.sqrt(n)

print("=" * 72)
print(f"DIAGNOSTIK RESIDUAL PROPHET (cps={DIAG_CPS} {DIAG_MODE}, start={START_YEAR}, n={n})")
print("=" * 72)
print(f"mean residual     : {res.mean():.2f}")
print(f"variance residual : {res.var(ddof=1):.1f}   std: {res.std(ddof=1):.1f}")
print(f"  [kontras] var residual Prophet FLEKSIBEL cps=0.5 (in-sample): "
      f"{res_flex.var(ddof=1):.4f}  std: {res_flex.std(ddof=1):.4f}")
print(f"pita signifikansi ACF/PACF (95%): +/- {band:.3f}")
print("\nACF  lag 1..6 :", np.round(acf_v[1:7], 3))
print("PACF lag 1..6 :", np.round(pacf_v[1:7], 3))
print(f"  -> |ACF|>band pada lag: {[k for k in range(1,NL+1) if abs(acf_v[k])>band]}")
print("\nLjung-Box (H0 = tidak ada autokorelasi / white noise):")
for h, Q, p in lb:
    flag = "SIGNIFIKAN (ada autokorelasi)" if p < 0.05 else "tidak signifikan (white noise)"
    print(f"  lag {h:2d}:  Q={Q:7.2f}  p={p:.4f}  -> {flag}")
print(f"\nShapiro-Wilk normalitas: W={sh_stat:.3f} p={sh_p:.4f} "
      f"-> {'normal' if sh_p>0.05 else 'menyimpang dari normal'}")
print(f"\nXGBoost memprediksi residual OUT-OF-SAMPLE (backtest 2024-26): "
      f"R^2 = {r2_oos:.3f}")
print("  (R^2<=0 artinya XGBoost tidak lebih baik dari menebak rata-rata "
      "-> residual tak terprediksi OOS)")

# --------------------------------------------------------------------------
# Figur 3x3
# --------------------------------------------------------------------------
fig, ax = plt.subplots(3, 3, figsize=(16, 13))

ax[0, 0].plot(w["tanggal"], res, marker="o", ms=3); ax[0, 0].axhline(0, color="r", lw=1)
ax[0, 0].set_title("1. Residual vs Waktu"); ax[0, 0].grid(alpha=.3)

ax[0, 1].hist(res, bins=15, density=True, color="steelblue", alpha=.7, edgecolor="w")
xs = np.linspace(res.min(), res.max(), 100)
ax[0, 1].plot(xs, stats.norm.pdf(xs, res.mean(), res.std()), "r-")
ax[0, 1].set_title(f"2. Histogram (var={res.var(ddof=1):.0f})"); ax[0, 1].grid(alpha=.3)

roll = pd.Series(res).rolling(6).std()
ax[0, 2].plot(w["tanggal"], roll, color="darkorange")
ax[0, 2].set_title("3. Rolling std residual (window 6)"); ax[0, 2].grid(alpha=.3)

ax[1, 0].bar(range(1, NL + 1), acf_v[1:], color="teal")
ax[1, 0].axhline(band, color="r", ls="--"); ax[1, 0].axhline(-band, color="r", ls="--")
ax[1, 0].set_title("4. ACF residual"); ax[1, 0].grid(alpha=.3)

ax[1, 1].bar(range(1, NL + 1), pacf_v[1:], color="indigo")
ax[1, 1].axhline(band, color="r", ls="--"); ax[1, 1].axhline(-band, color="r", ls="--")
ax[1, 1].set_title("5. PACF residual"); ax[1, 1].grid(alpha=.3)

lags_all = list(range(1, 13))
pv = [p for _, _, p in ljung_box(res, lags_all)]
ax[1, 2].plot(lags_all, pv, "o-", color="purple"); ax[1, 2].axhline(0.05, color="r", ls="--")
ax[1, 2].set_title("6. Ljung-Box p-value per lag"); ax[1, 2].set_ylim(-0.02, 1.02); ax[1, 2].grid(alpha=.3)

z = (res - res.mean()) / res.std()
theo = stats.norm.ppf((np.arange(1, n + 1) - 0.5) / n)
ax[2, 0].scatter(theo, np.sort(z), s=18); ax[2, 0].plot(theo, theo, "r-")
ax[2, 0].set_title("7. QQ-plot (normalitas)"); ax[2, 0].grid(alpha=.3)

ax[2, 1].scatter(w["yhat"], res, s=18); ax[2, 1].axhline(0, color="r")
ax[2, 1].set_title("8. Residual vs Fitted (yhat)"); ax[2, 1].grid(alpha=.3)

ax[2, 2].scatter(res_act_oos, res_pred_oos, s=25, color="green")
lim = [min(res_act_oos.min(), res_pred_oos.min()), max(res_act_oos.max(), res_pred_oos.max())]
ax[2, 2].plot(lim, lim, "r--"); ax[2, 2].axhline(0, color="gray", lw=.6); ax[2, 2].axvline(0, color="gray", lw=.6)
ax[2, 2].set_title(f"9. Residual aktual vs prediksi XGBoost (OOS, R2={r2_oos:.2f})")
ax[2, 2].set_xlabel("residual aktual"); ax[2, 2].set_ylabel("prediksi"); ax[2, 2].grid(alpha=.3)

plt.tight_layout()
out = os.path.join(PLOT_DIR, "residual_diagnostics.png")
plt.savefig(out, dpi=120); plt.close()
print(f"\nFigur disimpan: {out}")
