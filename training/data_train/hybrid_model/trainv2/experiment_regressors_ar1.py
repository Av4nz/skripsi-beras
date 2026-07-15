"""
============================================================================
 EKSPERIMEN VERIFIKASI (read-only) -- trainv2
 Prophet(+regressor eksternal) + Linear AR(1) residual
============================================================================
TIDAK menyentuh backend/ml_models maupun kode produksi. Hanya menghitung &
melaporkan angka untuk mendukung keputusan arsitektur skripsi.

Tujuan: menjawab apakah MEMAKAI SEMUA variabel eksternal (harga_gkg,
curah_hujan, produksi_padi, inflasi_pangan) sebagai REGRESSOR PROPHET (bukan
fitur residual learner) + koreksi residual Linear AR(1) itu:
  (a) masih di bawah ambang MAPE,
  (b) tiap variabel benar-benar berkontribusi (koefisien Prophet),
  (c) secara statistik berbeda dari Prophet-only (uji Diebold-Mariano).

Tiga konfigurasi dibandingkan (Prophet cps=0.5, sps=10, multiplicative =
konfigurasi yang dideploy; regressor eksternal: additive + standardized +
teregularisasi). Masing-masing + Linear AR(1) pada residual:
  A. Prophet-only        : regressor {lebaran}
  B. +gkg                : regressor {lebaran, harga_gkg}
  C. +semua eksternal    : regressor {lebaran, harga_gkg, curah_hujan,
                                       produksi_padi, inflasi_pangan}

Evaluasi: rolling backtest 2024/2025/2026 (expanding window), one-step &
recursive. Plus kontribusi regressor (config C) & Diebold-Mariano.

Jalankan:
    backend/.venv/Scripts/python.exe \
        backend/data_train/hybrid_model/trainv2/experiment_regressors_ar1.py
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
from prophet.utilities import regressor_coefficients
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_percentage_error, mean_absolute_error
from scipy import stats

warnings.filterwarnings("ignore")
logging.getLogger("cmdstanpy").setLevel(logging.ERROR)
logging.getLogger("prophet").setLevel(logging.ERROR)

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_PATH = os.path.abspath(
    os.path.join(SCRIPT_DIR, "..", "..", "datasets", "data_app",
                 "harga_beras_2018_2026.csv")
)

START_YEAR = 2021
BACKTEST_YEARS = [2024, 2025, 2026]

# Konfigurasi Prophet = yang dideploy (cps=0.5, sps=10, multiplicative).
PROPHET_CPS = 0.5
PROPHET_SPS = 10.0
PROPHET_MODE = "multiplicative"
# Regularisasi regressor eksternal (prior_scale kecil -> menyusut bila lemah).
REG_PRIOR_SCALE = 2.0

EXOG = ["harga_gkg", "curah_hujan", "produksi_padi", "inflasi_pangan"]
CONFIGS = {
    "A. Prophet-only": ["lebaran"],
    "B. +gkg": ["lebaran", "harga_gkg"],
    "C. +semua eksternal": ["lebaran"] + EXOG,
}


def mape(y, p):
    return mean_absolute_percentage_error(y, p)


# ---------------------------------------------------------------------------
def load_pool():
    pool = pd.read_csv(DATA_PATH)
    pool["tanggal"] = pd.to_datetime(pool["tanggal"])
    pool = pool.sort_values("tanggal").reset_index(drop=True)
    pool = pool[pool["tanggal"].dt.year >= START_YEAR].reset_index(drop=True)
    return pool


def fit_prophet(train_df, regressors):
    m = Prophet(
        yearly_seasonality=True, weekly_seasonality=False, daily_seasonality=False,
        changepoint_prior_scale=PROPHET_CPS, seasonality_prior_scale=PROPHET_SPS,
        seasonality_mode=PROPHET_MODE,
    )
    for r in regressors:
        if r == "lebaran":
            m.add_regressor("lebaran")  # default prior, mode ikut seasonality
        else:  # eksternal: additive & teregularisasi supaya interpretable + aman
            m.add_regressor(r, prior_scale=REG_PRIOR_SCALE, standardize=True,
                            mode="additive")
    cols = ["tanggal", "harga_beras"] + regressors
    p = train_df[cols].rename(columns={"tanggal": "ds", "harga_beras": "y"})
    m.fit(p)
    return m


def prophet_yhat(model, frame, regressors):
    cols = ["tanggal"] + regressors
    p = frame[cols].rename(columns={"tanggal": "ds"})
    return model.predict(p)["yhat"].values


def fit_ar1(residual_train):
    """OLS residual_t ~ 1 + residual_{t-1}. Kembalikan (intercept, phi)."""
    r = np.asarray(residual_train, dtype=float)
    x = r[:-1].reshape(-1, 1)
    y = r[1:]
    lr = LinearRegression().fit(x, y)
    return float(lr.intercept_), float(lr.coef_[0])


def eval_config(pool, regressors, test_year):
    """Expanding window: latih < test_year, uji test_year. One-step & recursive."""
    window = pool[pool["tanggal"].dt.year <= test_year].reset_index(drop=True)
    train = window[window["tanggal"].dt.year < test_year].reset_index(drop=True)
    test = window[window["tanggal"].dt.year == test_year].reset_index(drop=True)
    if len(test) == 0 or len(train) < 12:
        return None

    model = fit_prophet(train, regressors)

    # residual seluruh window (train+test) dari model yang dilatih di train
    window["yhat"] = prophet_yhat(model, window, regressors)
    window["residual"] = window["harga_beras"] - window["yhat"]
    tr_mask = window["tanggal"].dt.year < test_year
    te_mask = window["tanggal"].dt.year == test_year

    resid_train = window.loc[tr_mask, "residual"].values
    resid_test = window.loc[te_mask, "residual"].values
    yhat_test = window.loc[te_mask, "yhat"].values
    actual_test = window.loc[te_mask, "harga_beras"].values

    intercept, phi = fit_ar1(resid_train)

    # gabungan residual sepanjang [.. train terakhir, test..] untuk lag one-step
    resid_seq = np.concatenate([resid_train, resid_test])
    n_tr = len(resid_train)

    # one-step: residual_lag = AKTUAL bulan sebelumnya
    onestep = []
    for i in range(len(resid_test)):
        r_prev = resid_seq[n_tr + i - 1]  # aktual t-1
        r_hat = intercept + phi * r_prev
        onestep.append(yhat_test[i] + r_hat)
    onestep = np.array(onestep)

    # recursive: residual_lag = PREDIKSI sendiri (seed = residual train terakhir)
    recursive = []
    r_prev = resid_train[-1]
    for i in range(len(resid_test)):
        r_hat = intercept + phi * r_prev
        recursive.append(yhat_test[i] + r_hat)
        r_prev = r_hat
    recursive = np.array(recursive)

    return {
        "dates": window.loc[te_mask, "tanggal"].values,
        "actual": actual_test,
        "base": yhat_test,          # Prophet-only (regressor set ini)
        "onestep": onestep,         # hybrid one-step
        "recursive": recursive,     # hybrid recursive
        "phi": phi, "intercept": intercept,
        "model": model, "regressors": regressors,
    }


def diebold_mariano(actual, pred1, pred2, h=1):
    """DM (loss kuadrat). Negatif => pred2 lebih baik. HLN small-sample corr."""
    a = np.asarray(actual, float)
    e1 = a - np.asarray(pred1, float)
    e2 = a - np.asarray(pred2, float)
    d = e1**2 - e2**2
    n = len(d)
    dbar = d.mean()
    # variansi HAC untuk h-step (h=1 -> hanya gamma0)
    gamma0 = np.mean((d - dbar) ** 2)
    var_d = gamma0
    for k in range(1, h):
        cov = np.mean((d[k:] - dbar) * (d[:-k] - dbar))
        var_d += 2 * cov
    if var_d <= 0:
        return np.nan, np.nan
    dm = dbar / np.sqrt(var_d / n)
    hln = np.sqrt((n + 1 - 2 * h + h * (h - 1) / n) / n)
    dm_star = dm * hln
    p = 2 * stats.t.sf(abs(dm_star), df=n - 1)
    return float(dm_star), float(p)


# ===========================================================================
print("=" * 78)
print("EKSPERIMEN: Prophet(+regressor eksternal) + Linear AR(1)  [read-only]")
print("=" * 78)
pool = load_pool()
print(f"Data     : {DATA_PATH.split(os.sep)[-1]} | {pool['tanggal'].min().date()}"
      f"..{pool['tanggal'].max().date()} ({len(pool)} baris, mulai {START_YEAR})")
print(f"Prophet  : cps={PROPHET_CPS}, sps={PROPHET_SPS}, {PROPHET_MODE} | "
      f"regressor eksternal prior_scale={REG_PRIOR_SCALE} (additive, standardized)")
print(f"Backtest : {BACKTEST_YEARS} (expanding window)\n")

# jalankan semua konfigurasi x tahun
store = {name: {} for name in CONFIGS}
for name, regs in CONFIGS.items():
    for ty in BACKTEST_YEARS:
        res = eval_config(pool, regs, ty)
        if res is not None:
            store[name][ty] = res

# ---- tabel per konfigurasi (agregat semua titik backtest) -----------------
def pooled(name, key):
    a, p = [], []
    for ty in BACKTEST_YEARS:
        if ty in store[name]:
            a.extend(store[name][ty]["actual"])
            p.extend(store[name][ty][key])
    return np.array(a), np.array(p)

print("=" * 78)
print("HASIL ROLLING BACKTEST (agregat 2024-2026)")
print("=" * 78)
print(f"{'Konfigurasi':<22}{'Prophet-base':>13}{'Hybrid 1-step':>15}"
      f"{'Hybrid recursive':>18}")
print("-" * 78)
summary_rows = {}
for name in CONFIGS:
    a, base = pooled(name, "base")
    _, one = pooled(name, "onestep")
    _, rec = pooled(name, "recursive")
    m_base, m_one, m_rec = mape(a, base), mape(a, one), mape(a, rec)
    summary_rows[name] = {"base": m_base, "onestep": m_one, "recursive": m_rec,
                          "phi_per_year": {ty: store[name][ty]["phi"]
                                           for ty in store[name]}}
    print(f"{name:<22}{m_base:>12.2%}{m_one:>14.2%}{m_rec:>17.2%}")
print("-" * 78)

# ---- rincian per tahun untuk config C -------------------------------------
print("\nRincian per tahun -- C. +semua eksternal (one-step):")
for ty in BACKTEST_YEARS:
    if ty in store["C. +semua eksternal"]:
        r = store["C. +semua eksternal"][ty]
        print(f"   {ty}: base={mape(r['actual'], r['base']):.2%}  "
              f"hybrid1step={mape(r['actual'], r['onestep']):.2%}  "
              f"recursive={mape(r['actual'], r['recursive']):.2%}  "
              f"phi={r['phi']:.3f}")

# ---- kontribusi tiap regressor (config C, fit train<2025) -----------------
print("\n" + "=" * 78)
print("KONTRIBUSI REGRESSOR -- config C, model dilatih 2021..2024")
print("=" * 78)
mdl_C = store["C. +semua eksternal"][2025]["model"]
coefs = regressor_coefficients(mdl_C)
print(coefs.to_string(index=False))
print("(coef = efek pada harga per +1 SD regressor; additive & standardized)")

# ---- Diebold-Mariano ------------------------------------------------------
print("\n" + "=" * 78)
print("UJI DIEBOLD-MARIANO (loss kuadrat, h=1; negatif => model-2 lebih baik)")
print("=" * 78)
aA, A_base = pooled("A. Prophet-only", "base")
_, C_base = pooled("C. +semua eksternal", "base")
_, C_one = pooled("C. +semua eksternal", "onestep")
_, A_one = pooled("A. Prophet-only", "onestep")

tests = [
    ("A base (Prophet-only) vs C base (Prophet+exog)", A_base, C_base),
    ("A base (Prophet-only) vs C hybrid one-step", A_base, C_one),
    ("C base (Prophet+exog) vs C hybrid one-step (efek AR)", C_base, C_one),
    ("A hybrid (Prophet-only+AR) vs C hybrid (Prophet+exog+AR)", A_one, C_one),
]
dm_out = {}
for label, p1, p2 in tests:
    n = min(len(p1), len(p2))
    dm, pval = diebold_mariano(aA[:n], p1[:n], p2[:n], h=1)
    sig = "signifikan" if (pval is not np.nan and pval < 0.05) else "TIDAK signifikan"
    dm_out[label] = {"dm": dm, "p": pval, "n": int(n)}
    print(f"  {label}\n     DM*={dm:+.3f}  p={pval:.4f}  (n={n})  -> {sig}")

# ---- simpan ringkasan -----------------------------------------------------
out = {
    "prophet_config": {"cps": PROPHET_CPS, "sps": PROPHET_SPS, "mode": PROPHET_MODE,
                       "reg_prior_scale": REG_PRIOR_SCALE},
    "backtest_years": BACKTEST_YEARS,
    "aggregate_mape": summary_rows,
    "regressor_coefficients_C_2024fit": coefs.to_dict(orient="records"),
    "diebold_mariano": dm_out,
}
with open(os.path.join(SCRIPT_DIR, "experiment_regressors_ar1.json"), "w") as f:
    json.dump(out, f, indent=4, default=float)
print("\nTersimpan: experiment_regressors_ar1.json")
print("=" * 78)
