"""
============================================================================
 HYBRID PROPHET(+REGRESSOR EKSOGEN) + LINEAR AR  (trainv2)
============================================================================
Arsitektur berbasis-bukti (lihat residual_diagnostics.py):

    harga_beras = Prophet(tren + musiman + lebaran + eksogen)
                  + Linear-AR(residual)          # koreksi galat forecast

Alasan desain (dibuktikan, bukan asumsi):
  - Variabel eksogen (harga_gkg, curah_hujan, produksi_padi, inflasi_pangan)
    dipakai sebagai REGRESSOR PROPHET (tempat A) -> menurunkan error Prophet.
    (Di korektor residual mereka justru overfit karena n_train kecil.)
  - Residual Prophet punya autokorelasi AR (Ljung-Box p<0.0001) yang hanya
    bisa dieksploitasi model LINEAR yang bisa EKSTRAPOLASI. XGBoost/pohon gagal
    (OOS R^2~0.02) karena tak bisa ekstrapolasi galat forecast OOS.

Yang dituning (objektif: MAPE hybrid one-step pada tahun validasi):
  - set regressor Prophet, changepoint_prior_scale, seasonality_mode,
  - orde AR korektor residual (1 atau 2).

Evaluasi: rolling backtest 2024/2025/2026 (one-step & recursive), per tahun +
agregat, dibandingkan dengan Prophet-only dan (referensi) Prophet+XGBoost.

CATATAN DEPLOY: arsitektur ini butuh perubahan backend/predictor.py karena
(a) Prophet kini pakai regressor eksogen (harus dikirim saat predict), dan
(b) korektor residual = LinearRegression pada residual_lag. Artefak disimpan
terpisah; TIDAK menimpa model produksi lama.

Jalankan: backend/.venv/Scripts/python.exe \
          backend/data_train/hybrid_model/trainv2/train_hybrid_linear.py
============================================================================
"""
import os, json, logging, warnings
import numpy as np, pandas as pd, joblib
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from prophet import Prophet
from sklearn.linear_model import LinearRegression
from sklearn.metrics import (mean_absolute_error, mean_absolute_percentage_error,
                             root_mean_squared_error, r2_score)
from xgboost import XGBRegressor

warnings.filterwarnings("ignore")
logging.getLogger("cmdstanpy").setLevel(logging.ERROR)
logging.getLogger("prophet").setLevel(logging.ERROR)

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_PATH = os.path.abspath(os.path.join(SCRIPT_DIR, "..", "..", "datasets",
                            "data_app", "harga_beras_2018_2026.csv"))
PLOT_DIR = os.path.join(SCRIPT_DIR, "plots"); os.makedirs(PLOT_DIR, exist_ok=True)

START_YEAR = 2021
BACKTEST_YEARS = [2024, 2025, 2026]
VALIDATION_YEARS = [2024, 2025]
RANDOM_STATE = 42

REGRESSOR_SETS = {
    "lebaran":        ["lebaran"],
    "+gkg":           ["lebaran", "harga_gkg"],
    "+all_exog":      ["lebaran", "harga_gkg", "curah_hujan", "produksi_padi", "inflasi_pangan"],
}
CPS_GRID = [0.05, 0.3, 0.5]
MODE_GRID = ["additive", "multiplicative"]
AR_ORDERS = [1, 2]

# Fitur XGBoost (referensi pembanding) - 11 fitur non-leaky seperti versi lama.
XGB_FEATURES = ["harga_gkg", "curah_hujan", "produksi_padi", "inflasi_pangan",
                "lag_1", "lag_2", "rolling_mean_3", "residual_lag_1",
                "residual_lag_2", "month_sin", "month_cos"]


def mape(y, p): return mean_absolute_percentage_error(y, p)


# ---------------------------------------------------------------------------
def fit_prophet(train, regs, cps, mode):
    m = Prophet(yearly_seasonality=True, weekly_seasonality=False,
                daily_seasonality=False, changepoint_prior_scale=cps,
                seasonality_prior_scale=10.0, seasonality_mode=mode)
    for r in regs:
        m.add_regressor(r)
    m.fit(train[["tanggal", "harga_beras"] + regs].rename(
        columns={"tanggal": "ds", "harga_beras": "y"}))
    return m


def prophet_predict(m, frame, regs):
    return m.predict(frame[["tanggal"] + regs].rename(columns={"tanggal": "ds"}))["yhat"].values


def build_frame(pool, start, end, regs, cps, mode, fit_end):
    """Window [start..end], Prophet(fit_end) + residual + fitur (residual_lag &
    fitur harga untuk XGBoost referensi)."""
    w = pool[(pool.tanggal.dt.year >= start) & (pool.tanggal.dt.year <= end)].copy().reset_index(drop=True)
    # fitur harga (hanya utk pembanding XGBoost)
    w["lag_1"] = w["harga_beras"].shift(1); w["lag_2"] = w["harga_beras"].shift(2)
    w["rolling_mean_3"] = w["harga_beras"].shift(1).rolling(3).mean()
    mth = w["tanggal"].dt.month
    w["month_sin"] = np.sin(2*np.pi*mth/12); w["month_cos"] = np.cos(2*np.pi*mth/12)
    m = fit_prophet(w[w.tanggal.dt.year <= fit_end], regs, cps, mode)
    w["yhat"] = prophet_predict(m, w, regs)
    w["residual"] = w["harga_beras"] - w["yhat"]
    w["residual_lag_1"] = w["residual"].shift(1)
    w["residual_lag_2"] = w["residual"].shift(2)
    return m, w


def ar_cols(order): return ["residual_lag_1"] if order == 1 else ["residual_lag_1", "residual_lag_2"]


def eval_config(pool, start, regs, cps, mode, order, test_year):
    m, w = build_frame(pool, start, test_year, regs, cps, mode, fit_end=test_year - 1)
    cols = ar_cols(order)
    w = w.dropna(subset=cols).reset_index(drop=True)
    tr = w[w.tanggal.dt.year < test_year]; te = w[w.tanggal.dt.year == test_year]
    if len(te) == 0 or len(tr) < 12:
        return None
    lr = LinearRegression().fit(tr[cols], tr["residual"])
    hybrid = te["yhat"].values + lr.predict(te[cols])
    return {"actual": te["harga_beras"].values, "yhat": te["yhat"].values,
            "hybrid": hybrid, "mape": mape(te["harga_beras"], hybrid)}


# ===========================================================================
print("=" * 78); print("1. Load:", DATA_PATH)
pool = pd.read_csv(DATA_PATH); pool["tanggal"] = pd.to_datetime(pool["tanggal"])
pool = pool.sort_values("tanggal").reset_index(drop=True)
print(f"   {len(pool)} baris ({pool.tanggal.min().date()}..{pool.tanggal.max().date()})")

# ---------------------------------------------------------------------------
print("\n" + "=" * 78)
print("2. Tuning (regressor set + cps + mode + orde AR) via MAPE hybrid validasi",
      VALIDATION_YEARS)
best = {"mape": np.inf}
for rname, regs in REGRESSOR_SETS.items():
    for cps in CPS_GRID:
        for mode in MODE_GRID:
            for order in AR_ORDERS:
                vals = []
                for vy in VALIDATION_YEARS:
                    try:
                        r = eval_config(pool, START_YEAR, regs, cps, mode, order, vy)
                    except Exception:
                        r = None
                    if r is None: break
                    vals.append(r["mape"])
                if len(vals) == len(VALIDATION_YEARS):
                    avg = float(np.mean(vals))
                    if avg < best["mape"]:
                        best = {"mape": avg, "regs": regs, "rname": rname,
                                "cps": cps, "mode": mode, "order": order}
print(f"   Terbaik -> regressor='{best['rname']}' {best['regs']}")
print(f"             cps={best['cps']} mode={best['mode']} AR({best['order']}) "
      f"| val MAPE={best['mape']:.2%}")

# ---------------------------------------------------------------------------
print("\n" + "=" * 78)
print(f"3. Rolling backtest {BACKTEST_YEARS} (start {START_YEAR}) ...")
cols = ar_cols(best["order"])
rows, A, Yp, Hh, Hr, Xr = [], [], [], [], [], []
ra_oos, rp_oos = [], []
for ty in BACKTEST_YEARS:
    m, w = build_frame(pool, START_YEAR, ty, best["regs"], best["cps"], best["mode"], fit_end=ty-1)
    ww = w.dropna(subset=["residual_lag_1", "residual_lag_2", "lag_1", "lag_2", "rolling_mean_3"]).reset_index(drop=True)
    tr = ww[ww.tanggal.dt.year < ty]; te = ww[ww.tanggal.dt.year == ty]
    # Prophet + Linear AR (one-step)
    lr = LinearRegression().fit(tr[cols], tr["residual"])
    hyb = te["yhat"].values + lr.predict(te[cols])
    # recursive (residual_lag pakai prediksi sendiri)
    hr = list(tr["residual"].values); rec = []
    for i in range(len(te)):
        r1 = hr[-1]; feat = [[r1]] if best["order"] == 1 else [[r1, hr[-2]]]
        pr = float(lr.predict(feat)[0]); rec.append(float(te["yhat"].values[i]) + pr); hr.append(pr)
    # XGBoost referensi (11 fitur) di atas Prophet yang SAMA
    xgb = XGBRegressor(n_estimators=60, learning_rate=0.05, max_depth=3,
                       subsample=0.8, colsample_bytree=0.8, random_state=RANDOM_STATE)
    xgb.fit(tr[XGB_FEATURES], tr["residual"])
    xgbpred = te["yhat"].values + xgb.predict(te[XGB_FEATURES])

    A += list(te["harga_beras"].values); Yp += list(te["yhat"].values)
    Hh += list(hyb); Hr += list(rec); Xr += list(xgbpred)
    ra_oos += list(te["residual"].values); rp_oos += list(lr.predict(te[cols]))
    rows.append({"year": ty, "n": len(te),
                 "prophet_only": mape(te["harga_beras"], te["yhat"]),
                 "hybrid_linear": mape(te["harga_beras"], hyb),
                 "hybrid_recursive": mape(te["harga_beras"], rec),
                 "xgb_ref": mape(te["harga_beras"], xgbpred),
                 "tanggal": te["tanggal"].values})
    print(f"   [{ty}] Prophet={rows[-1]['prophet_only']:.2%} | "
          f"Prophet+LinearAR={rows[-1]['hybrid_linear']:.2%} "
          f"(recursive {rows[-1]['hybrid_recursive']:.2%}) | XGB ref={rows[-1]['xgb_ref']:.2%}")

agg = {"prophet_only": mape(A, Yp), "hybrid_linear": mape(A, Hh),
       "hybrid_recursive": mape(A, Hr), "xgb_ref": mape(A, Xr),
       "hybrid_mae": mean_absolute_error(A, Hh), "hybrid_rmse": root_mean_squared_error(A, Hh),
       "residual_oos_r2": r2_score(ra_oos, rp_oos)}
print("   " + "-" * 60)
print(f"   AGREGAT ({len(A)} titik):")
print(f"     Prophet-only        : {agg['prophet_only']:.2%}")
print(f"     Prophet + Linear AR : {agg['hybrid_linear']:.2%}  "
      f"MAE={agg['hybrid_mae']:.1f} RMSE={agg['hybrid_rmse']:.1f}  (recursive {agg['hybrid_recursive']:.2%})")
print(f"     [ref] Prophet+XGB   : {agg['xgb_ref']:.2%}")
print(f"     Residual OOS R^2 (Linear AR): {agg['residual_oos_r2']:+.3f}")

# ---------------------------------------------------------------------------
print("\n" + "=" * 78); print("4. Plot & simpan artefak ...")
tgl = np.concatenate([r["tanggal"] for r in rows])
plt.figure(figsize=(14, 6))
plt.plot(tgl, A, "o-", label="Actual", color="blue", lw=2)
plt.plot(tgl, Yp, "x--", label="Prophet-only", color="red", alpha=.6)
plt.plot(tgl, Hh, "D-", label="Prophet + Linear AR", color="green")
plt.plot(tgl, Xr, "s:", label="Prophet + XGBoost (ref)", color="gray", alpha=.7)
for r in rows:
    plt.axvline(pd.Timestamp(f"{r['year']}-01-01"), color="gray", ls=":", alpha=.3)
plt.title("Backtest: Prophet+Linear AR vs Prophet-only vs Prophet+XGBoost")
plt.xlabel("Tanggal"); plt.ylabel("Harga Beras"); plt.grid(alpha=.3); plt.legend()
plt.tight_layout(); plt.savefig(os.path.join(PLOT_DIR, "backtest_linear.png"), dpi=120); plt.close()

# Model produksi final: fit pada SELURUH data (fit_end = tahun maks)
final_end = int(pool.tanggal.dt.year.max())
prophet_final, wf = build_frame(pool, START_YEAR, final_end, best["regs"],
                                best["cps"], best["mode"], fit_end=final_end)
wf = wf.dropna(subset=cols).reset_index(drop=True)
lr_final = LinearRegression().fit(wf[cols], wf["residual"])
print(f"   Koefisien Linear AR({best['order']}): "
      f"{dict(zip(cols, np.round(lr_final.coef_,4)))}, intercept={lr_final.intercept_:.2f}")

joblib.dump(prophet_final, os.path.join(SCRIPT_DIR, "prophet_model_linear.pkl"))
joblib.dump(lr_final, os.path.join(SCRIPT_DIR, "linear_residual_model.pkl"))
with open(os.path.join(SCRIPT_DIR, "features_linear.json"), "w") as f:
    json.dump({"prophet_regressors": best["regs"], "residual_features": cols}, f, indent=4)
summary = {"architecture": "Prophet(+exog regressors) + Linear AR residual",
           "prophet_regressors": best["regs"], "changepoint_prior_scale": best["cps"],
           "seasonality_mode": best["mode"], "ar_order": best["order"],
           "train_window": f"{START_YEAR}..{final_end}",
           "per_year": [{k: r[k] for k in ["year","prophet_only","hybrid_linear","hybrid_recursive","xgb_ref"]} for r in rows],
           "aggregate": {k: agg[k] for k in agg}}
with open(os.path.join(SCRIPT_DIR, "metrics_summary_linear.json"), "w") as f:
    json.dump(summary, f, indent=4, default=float)
print("   Tersimpan: prophet_model_linear.pkl, linear_residual_model.pkl, "
      "features_linear.json, metrics_summary_linear.json, plots/backtest_linear.png")

print("\n" + "=" * 78)
print("RINGKASAN")
print(f"  Arsitektur : Prophet(+{best['regs']}) cps={best['cps']} {best['mode']} + Linear AR({best['order']})")
print(f"  Agregat    : Prophet {agg['prophet_only']:.2%} -> +Linear AR {agg['hybrid_linear']:.2%} "
      f"| XGB ref {agg['xgb_ref']:.2%}")
print("=" * 78)
