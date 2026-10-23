"""
============================================================================
 TRAINING ULANG -- SKEMA REALISTIS (prediksi 1 bulan ke depan) -- trainv3
============================================================================
Masalah pada skema lama (trainv2, mode "skenario"):
    harga(T) diprediksi memakai faktor eksternal bulan T itu sendiri.
    Saat memprediksi bulan depan, nilai faktor eksternal bulan depan belum
    diketahui, jadi angka akurasinya terlalu optimistis.

Skema realistis (skrip ini):
    harga(T+1) = f( informasi yang SUDAH diketahui pada akhir bulan T )
        - faktor eksternal bulan T : harga_gkg, curah_hujan, produksi_padi,
                                     inflasi_pangan  (+ selisih gkg T vs T-1)
        - harga beras bulan T, T-1, T-2 dan rata-rata 3 bulan terakhir
        - kalender bulan target   : month_sin/cos(T+1), lebaran(T+1)
          (jadwal Lebaran & nomor bulan sudah pasti diketahui sebelumnya)

Model yang dibandingkan (arsitektur sama seperti sebelumnya):
    1. Prophet-only  : y(T+1) ~ trend + yearly + lebaran(T+1) [+ exog(T)]
    2. XGBoost-only  : y(T+1) langsung dari fitur di atas
                       (target level harga, atau selisih harga dari bulan T)
    3. Hybrid        : Prophet(T+1) + XGBoost(residual Prophet)
    + Baseline naive : harga(T+1) = harga(T)   (pembanding wajib)

Protokol evaluasi (walk-forward, expanding window, refit tiap bulan):
    Data target mulai : 2021-01 (rezim harga 2018-2020 tidak dipakai sbg target,
                        tetapi nilainya dipakai untuk fitur lag Des 2020)
    Validasi (tuning) : target 2023-01 .. 2023-12  (12 bulan)
    Uji (laporan)     : target 2024-01 .. 2026-05  (29 bulan, tidak pernah
                        dilihat saat tuning)
    Untuk tiap bulan target M: model dilatih pada semua baris dengan target
    < M, lalu memprediksi M. Tidak ada informasi masa depan yang dipakai.

Hyperparameter dituning per model (grid / random search pada validasi 2023,
kriteria MAPE). Konfigurasi default (tanpa tuning) juga dilaporkan.

Output (semua di folder ini, file lama TIDAK disentuh):
    tuning_prophet.csv, tuning_xgboost.csv, tuning_hybrid.csv
    predictions_test.csv, results.json
    final_prophet.pkl, final_xgboost.pkl, final_hybrid_prophet.pkl,
    final_hybrid_xgboost.pkl, final_config.json

Jalankan dari root repo:
    backend/.venv/Scripts/python.exe \
        training/data_train/hybrid_model/trainv3_realistic/train_realistic.py
============================================================================
"""

import os
import json
import time
import random
import logging
import warnings
import itertools

import numpy as np
import pandas as pd
import joblib

# pyrefly: ignore [missing-import]
from prophet import Prophet
from sklearn.metrics import (mean_absolute_error,
                             mean_absolute_percentage_error,
                             root_mean_squared_error)
from xgboost import XGBRegressor
from joblib import Parallel, delayed

warnings.filterwarnings("ignore")
logging.getLogger("cmdstanpy").setLevel(logging.ERROR)
logging.getLogger("prophet").setLevel(logging.ERROR)

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_PATH = os.path.abspath(os.path.join(SCRIPT_DIR, "..", "trainv2",
                                         "harga_beras_2018_2026.csv"))

RANDOM_STATE = 42
N_JOBS = max(1, (os.cpu_count() or 2) - 1)
TARGET_START = "2021-01-01"
VAL_START, VAL_END = "2023-01-01", "2023-12-01"
TEST_START = "2024-01-01"
N_XGB_SAMPLES = 80          # jumlah konfigurasi random search XGBoost-only
N_HYB_SAMPLES = 60          # jumlah konfigurasi random search XGBoost hybrid
N_HYB_PROPHET = 3           # top-k konfigurasi Prophet yang dicoba di hybrid
SMOKE = os.environ.get("SMOKE") == "1"   # uji cepat alur kode saja
if SMOKE:
    N_XGB_SAMPLES, N_HYB_SAMPLES, N_HYB_PROPHET = 2, 2, 1

EXOG = ["harga_gkg", "curah_hujan", "produksi_padi", "inflasi_pangan"]
EXOG_T = [f"{c}_t" for c in EXOG] + ["gkg_diff_t"]
AR_FEATS = ["price_t", "price_t1", "price_t2", "rolling_mean_3", "diff_t"]
CAL_FEATS = ["month_sin", "month_cos", "lebaran_next"]
RESID_FEATS = ["resid_lag1", "resid_lag2"]


# ============================================================================
# 1. DATA: setiap baris = (informasi bulan T) -> target harga bulan T+1
# ============================================================================
def build_frame():
    raw = pd.read_csv(DATA_PATH)
    raw["tanggal"] = pd.to_datetime(raw["tanggal"])
    raw = raw.sort_values("tanggal").reset_index(drop=True)

    f = pd.DataFrame()
    f["ds"] = raw["tanggal"].shift(-1)                 # bulan target T+1
    f["y"] = raw["harga_beras"].shift(-1)              # harga target T+1
    f["origin"] = raw["tanggal"]                       # bulan informasi T
    for c in EXOG:
        f[f"{c}_t"] = raw[c]
    f["gkg_diff_t"] = raw["harga_gkg"].diff()
    f["price_t"] = raw["harga_beras"]
    f["price_t1"] = raw["harga_beras"].shift(1)
    f["price_t2"] = raw["harga_beras"].shift(2)
    f["rolling_mean_3"] = raw["harga_beras"].rolling(3).mean()
    f["diff_t"] = raw["harga_beras"].diff()
    f["lebaran_next"] = raw["lebaran"].shift(-1)
    month = f["ds"].dt.month
    f["month_sin"] = np.sin(2 * np.pi * month / 12)
    f["month_cos"] = np.cos(2 * np.pi * month / 12)

    f = f[f["ds"] >= TARGET_START].dropna().reset_index(drop=True)
    return raw, f


def metrics(y, p):
    y, p = np.asarray(y, float), np.asarray(p, float)
    return {"MAE": float(mean_absolute_error(y, p)),
            "RMSE": float(root_mean_squared_error(y, p)),
            "MAPE": float(mean_absolute_percentage_error(y, p))}


# ============================================================================
# 2. PROPHET
# ============================================================================
def fit_prophet(train, cfg):
    m = Prophet(yearly_seasonality=int(cfg["yearly_order"]), weekly_seasonality=False,
                daily_seasonality=False,
                changepoint_prior_scale=cfg["changepoint_prior_scale"],
                seasonality_prior_scale=cfg["seasonality_prior_scale"],
                seasonality_mode=cfg["seasonality_mode"])
    m.add_regressor("lebaran_next")
    regs = ["lebaran_next"]
    if cfg["use_exog"]:
        for c in EXOG_T:
            m.add_regressor(c, prior_scale=cfg["reg_prior_scale"],
                            standardize=True, mode="additive")
        regs += EXOG_T
    m.fit(train[["ds", "y"] + regs])
    return m, regs


def prophet_predict(model_regs, frame):
    m, regs = model_regs
    return m.predict(frame[["ds"] + regs])["yhat"].values


_PROPHET_CACHE = {}


def prophet_walk(frame, cfg, targets):
    """Refit Prophet tiap bulan target. Return {target_idx: (model, regs)}."""
    key = json.dumps(cfg, sort_keys=True)
    cache = _PROPHET_CACHE.setdefault(key, {})
    for i in targets:
        if i not in cache:
            cache[i] = fit_prophet(frame.iloc[:i], cfg)
    return cache


def eval_prophet(frame, cfg, targets):
    models = prophet_walk(frame, cfg, targets)
    return np.array([prophet_predict(models[i], frame.iloc[[i]])[0]
                     for i in targets])


# ============================================================================
# 3. XGBOOST-ONLY
# ============================================================================
def xgb_feats(cfg):
    return AR_FEATS + CAL_FEATS + (EXOG_T if cfg["use_exog"] else [])


def split_xgb_params(cfg):
    return {k: v for k, v in cfg.items()
            if k not in ("use_exog", "target_mode")}


def fit_xgb_only(train, cfg):
    feats = xgb_feats(cfg)
    target = train["y"] - train["price_t"] if cfg["target_mode"] == "diff" \
        else train["y"]
    model = XGBRegressor(random_state=RANDOM_STATE, n_jobs=1,
                         **split_xgb_params(cfg))
    model.fit(train[feats], target)
    return model


def predict_xgb_only(model, row, cfg):
    p = model.predict(row[xgb_feats(cfg)])
    return p + row["price_t"].values if cfg["target_mode"] == "diff" else p


def eval_xgb_only(frame, cfg, targets):
    out = []
    for i in targets:
        model = fit_xgb_only(frame.iloc[:i], cfg)
        out.append(predict_xgb_only(model, frame.iloc[[i]], cfg)[0])
    return np.array(out)


# ============================================================================
# 4. HYBRID: Prophet + XGBoost(residual)
# ============================================================================
def hybrid_feats(cfg):
    return RESID_FEATS + AR_FEATS + CAL_FEATS + (EXOG_T if cfg["use_exog"] else [])


def residual_frame(frame_upto, model_regs):
    """frame_upto = baris latih + 1 baris target terakhir. Residual in-sample
    dihitung pada baris latih, lalu digeser (lag) sehingga baris target hanya
    memakai residual bulan-bulan yang sudah lewat."""
    f = frame_upto.copy()
    f["yhat"] = prophet_predict(model_regs, f)
    resid = f["y"] - f["yhat"]
    resid.iloc[-1] = np.nan                       # y target belum diketahui
    f["resid_lag1"] = resid.shift(1)
    f["resid_lag2"] = resid.shift(2)
    f["resid"] = resid
    return f


def fit_predict_hybrid(frame, i, model_regs, cfg):
    f = residual_frame(frame.iloc[:i + 1], model_regs)
    train = f.iloc[:i].dropna(subset=RESID_FEATS + ["resid"])
    model = XGBRegressor(random_state=RANDOM_STATE, n_jobs=1,
                         **split_xgb_params(cfg))
    feats = hybrid_feats(cfg)
    model.fit(train[feats], train["resid"])
    row = f.iloc[[i]]
    return float(row["yhat"].values[0] + model.predict(row[feats])[0]), model


def eval_hybrid(frame, p_cfg, x_cfg, targets, models=None):
    if models is None:
        models = prophet_walk(frame, p_cfg, targets)
    return np.array([fit_predict_hybrid(frame, i, models[i], x_cfg)[0]
                     for i in targets])


# ============================================================================
# 5. RUANG HYPERPARAMETER
# ============================================================================
PROPHET_DEFAULT = {"changepoint_prior_scale": 0.05, "seasonality_prior_scale": 10.0,
                   "seasonality_mode": "additive", "yearly_order": 10,
                   "use_exog": True, "reg_prior_scale": 10.0}
XGB_DEFAULT_CORE = {"n_estimators": 100, "learning_rate": 0.3, "max_depth": 6,
                    "subsample": 1.0, "colsample_bytree": 1.0,
                    "min_child_weight": 1, "gamma": 0.0, "reg_alpha": 0.0,
                    "reg_lambda": 1.0}
XGB_ONLY_DEFAULT = {**XGB_DEFAULT_CORE, "use_exog": True, "target_mode": "level"}
HYB_XGB_DEFAULT = {**XGB_DEFAULT_CORE, "use_exog": True, "target_mode": "resid"}


def prophet_grid():
    if SMOKE:
        return [PROPHET_DEFAULT, {**PROPHET_DEFAULT, "use_exog": False,
                                  "reg_prior_scale": None, "yearly_order": 3}]
    grid = []
    for cps, sps, mode, fo in itertools.product([0.01, 0.05, 0.1, 0.5],
                                                [0.1, 1.0, 10.0],
                                                ["additive", "multiplicative"],
                                                [3, 5]):
        base = {"changepoint_prior_scale": cps, "seasonality_prior_scale": sps,
                "seasonality_mode": mode, "yearly_order": fo}
        grid.append({**base, "use_exog": False, "reg_prior_scale": None})
        for rps in [0.5, 2.0, 10.0]:
            grid.append({**base, "use_exog": True, "reg_prior_scale": rps})
    return grid


XGB_SPACE = {
    "n_estimators": [50, 100, 200, 400],
    "learning_rate": [0.01, 0.03, 0.05, 0.1, 0.3],
    "max_depth": [2, 3, 4, 6],
    "subsample": [0.6, 0.8, 1.0],
    "colsample_bytree": [0.6, 0.8, 1.0],
    "min_child_weight": [1, 3, 5],
    "gamma": [0.0],
    "reg_alpha": [0.0, 0.1, 1.0],
    "reg_lambda": [0.5, 1.0, 5.0],
}


def sample_xgb(n, seed, extra):
    rng = random.Random(seed)
    out = []
    for _ in range(n):
        cfg = {k: rng.choice(v) for k, v in XGB_SPACE.items()}
        cfg.update({k: rng.choice(v) for k, v in extra.items()})
        out.append(cfg)
    return out


# ============================================================================
# 6. MAIN
# ============================================================================
def main():
    t0 = time.time()
    raw, frame = build_frame()
    val_idx = frame.index[(frame["ds"] >= VAL_START) & (frame["ds"] <= VAL_END)].tolist()
    test_idx = frame.index[frame["ds"] >= TEST_START].tolist()
    y_val = frame.loc[val_idx, "y"].values
    y_test = frame.loc[test_idx, "y"].values

    print("=" * 78)
    print("TRAINING ULANG -- SKEMA REALISTIS: info bulan T -> harga bulan T+1")
    print("=" * 78)
    print(f"Dataset   : {DATA_PATH}")
    print(f"Target    : {frame['ds'].min().date()} .. {frame['ds'].max().date()} "
          f"({len(frame)} baris)")
    print(f"Validasi  : {len(val_idx)} bulan (2023), Uji: {len(test_idx)} bulan "
          f"({frame.loc[test_idx[0], 'ds'].date()} .. {frame.loc[test_idx[-1], 'ds'].date()})")

    # ---- 6.1 Tuning Prophet ------------------------------------------------
    print("\n[1/3] Tuning Prophet (grid, paralel) ...")
    grid = prophet_grid()
    vals = Parallel(n_jobs=N_JOBS)(
        delayed(_val_prophet)(frame, cfg, val_idx) for cfg in grid)
    rows = [{**cfg, **{f"val_{m}": v for m, v in metrics(y_val, p).items()}}
            for cfg, p in zip(grid, vals)]
    print(f"   {len(grid)} konfigurasi selesai ({time.time() - t0:.0f}s)")
    tune_p = pd.DataFrame(rows).sort_values("val_MAPE").reset_index(drop=True)
    _save(tune_p, "tuning_prophet.csv")
    best_p = _row_to_cfg(tune_p.iloc[0], PROPHET_DEFAULT)
    print("   Terbaik:", best_p, f"val MAPE={tune_p.iloc[0]['val_MAPE']:.3%}")

    # ---- 6.2 Tuning XGBoost-only -------------------------------------------
    print("\n[2/3] Tuning XGBoost-only (random search) ...")
    cands = [XGB_ONLY_DEFAULT] + sample_xgb(
        N_XGB_SAMPLES, RANDOM_STATE,
        {"use_exog": [True, False], "target_mode": ["level", "diff"]})
    vals = Parallel(n_jobs=N_JOBS)(
        delayed(eval_xgb_only)(frame, cfg, val_idx) for cfg in cands)
    rows = [{**cfg, **{f"val_{m}": v for m, v in metrics(y_val, p).items()}}
            for cfg, p in zip(cands, vals)]
    tune_x = pd.DataFrame(rows).sort_values("val_MAPE").reset_index(drop=True)
    _save(tune_x, "tuning_xgboost.csv")
    best_x = _row_to_cfg(tune_x.iloc[0], XGB_ONLY_DEFAULT)
    print("   Terbaik:", best_x, f"val MAPE={tune_x.iloc[0]['val_MAPE']:.3%}")
    print(f"   ({time.time() - t0:.0f}s)")

    # ---- 6.3 Tuning Hybrid -------------------------------------------------
    print("\n[3/3] Tuning Hybrid (top Prophet x random search XGBoost) ...")
    top_p = [_row_to_cfg(tune_p.iloc[j], PROPHET_DEFAULT) for j in range(N_HYB_PROPHET)]
    x_cands = [HYB_XGB_DEFAULT] + sample_xgb(
        N_HYB_SAMPLES, RANDOM_STATE + 1, {"use_exog": [True, False],
                                          "target_mode": ["resid"]})
    rows = []
    for pj, p_cfg in enumerate(top_p):
        models = {i: m for i, m in prophet_walk(frame, p_cfg, val_idx).items()
                  if i in val_idx}             # fit sekali, dikirim ke worker
        vals = Parallel(n_jobs=N_JOBS)(
            delayed(eval_hybrid)(frame, p_cfg, x_cfg, val_idx, models)
            for x_cfg in x_cands)
        for x_cfg, p in zip(x_cands, vals):
            rows.append({"prophet_rank": pj + 1,
                         **{f"p_{k}": v for k, v in p_cfg.items()},
                         **{f"x_{k}": v for k, v in x_cfg.items()},
                         **{f"val_{m}": v for m, v in metrics(y_val, p).items()}})
        print(f"   Prophet top-{pj + 1} selesai ({time.time() - t0:.0f}s)")
    tune_h = pd.DataFrame(rows).sort_values("val_MAPE").reset_index(drop=True)
    _save(tune_h, "tuning_hybrid.csv")
    best_hp = _row_to_cfg(tune_h.iloc[0], PROPHET_DEFAULT, prefix="p_")
    best_hx = _row_to_cfg(tune_h.iloc[0], HYB_XGB_DEFAULT, prefix="x_")
    print("   Terbaik Prophet:", best_hp)
    print("   Terbaik XGBoost:", best_hx, f"val MAPE={tune_h.iloc[0]['val_MAPE']:.3%}")

    # ---- 6.4 Evaluasi pada data UJI ----------------------------------------
    print("\nEvaluasi data uji (walk-forward, refit tiap bulan) ...")
    preds = {
        "Naive (harga bulan ini)": frame.loc[test_idx, "price_t"].values,
        "Prophet-only (default)": eval_prophet(frame, PROPHET_DEFAULT, test_idx),
        "Prophet-only (tuned)": eval_prophet(frame, best_p, test_idx),
        "XGBoost-only (default)": eval_xgb_only(frame, XGB_ONLY_DEFAULT, test_idx),
        "XGBoost-only (tuned)": eval_xgb_only(frame, best_x, test_idx),
        "Hybrid (default)": eval_hybrid(frame, PROPHET_DEFAULT, HYB_XGB_DEFAULT, test_idx),
        "Hybrid (tuned)": eval_hybrid(frame, best_hp, best_hx, test_idx),
    }
    val_preds = {
        "Naive (harga bulan ini)": frame.loc[val_idx, "price_t"].values,
        "Prophet-only (default)": eval_prophet(frame, PROPHET_DEFAULT, val_idx),
        "Prophet-only (tuned)": eval_prophet(frame, best_p, val_idx),
        "XGBoost-only (default)": eval_xgb_only(frame, XGB_ONLY_DEFAULT, val_idx),
        "XGBoost-only (tuned)": eval_xgb_only(frame, best_x, val_idx),
        "Hybrid (default)": eval_hybrid(frame, PROPHET_DEFAULT, HYB_XGB_DEFAULT, val_idx),
        "Hybrid (tuned)": eval_hybrid(frame, best_hp, best_hx, val_idx),
    }

    test_years = frame.loc[test_idx, "ds"].dt.year.values
    results = {}
    for name, p in preds.items():
        per_year = {int(y): metrics(y_test[test_years == y], p[test_years == y])
                    for y in sorted(set(test_years))}
        actual_dir = np.sign(y_test - frame.loc[test_idx, "price_t"].values)
        pred_dir = np.sign(p - frame.loc[test_idx, "price_t"].values)
        results[name] = {"validation_2023": metrics(y_val, val_preds[name]),
                         "test": metrics(y_test, p), "test_per_year": per_year,
                         "direction_acc_test": float(np.mean(actual_dir == pred_dir))}

    pred_df = frame.loc[test_idx, ["origin", "ds", "y"]].rename(
        columns={"origin": "bulan_info_T", "ds": "bulan_target_T+1",
                 "y": "aktual"}).reset_index(drop=True)
    for name, p in preds.items():
        pred_df[name] = np.round(p, 2)
    _save(pred_df, "predictions_test.csv")

    print("\n" + "=" * 78)
    print(f"{'Model':<28}{'val MAPE':>10}{'MAE':>10}{'RMSE':>10}{'MAPE':>9}{'Arah':>8}")
    for name, r in results.items():
        t = r["test"]
        print(f"{name:<28}{r['validation_2023']['MAPE']:>9.2%}{t['MAE']:>10.1f}"
              f"{t['RMSE']:>10.1f}{t['MAPE']:>9.2%}{r['direction_acc_test']:>8.0%}")

    # ---- 6.5 Model FINAL (seluruh data) + prakiraan bulan berikutnya -------
    print("\nMelatih model final pada seluruh data ...")
    last = raw.iloc[-1]
    nxt = pd.DataFrame([{
        "ds": last["tanggal"] + pd.DateOffset(months=1),
        **{f"{c}_t": last[c] for c in EXOG},
        "gkg_diff_t": last["harga_gkg"] - raw.iloc[-2]["harga_gkg"],
        "price_t": last["harga_beras"], "price_t1": raw.iloc[-2]["harga_beras"],
        "price_t2": raw.iloc[-3]["harga_beras"],
        "rolling_mean_3": raw["harga_beras"].iloc[-3:].mean(),
        "diff_t": last["harga_beras"] - raw.iloc[-2]["harga_beras"],
        "lebaran_next": np.nan, "y": np.nan,
    }])
    nxt["month_sin"] = np.sin(2 * np.pi * nxt["ds"].dt.month / 12)
    nxt["month_cos"] = np.cos(2 * np.pi * nxt["ds"].dt.month / 12)
    # Lebaran: Idul Fitri 2026 jatuh di Maret; Juni 2026 bukan bulan lebaran.
    nxt["lebaran_next"] = 0
    full_plus = pd.concat([frame, nxt], ignore_index=True)
    n = len(frame)

    p_final = fit_prophet(frame, best_p)
    x_final = fit_xgb_only(frame, best_x)
    hp_final = fit_prophet(frame, best_hp)
    h_pred, hx_final = fit_predict_hybrid(full_plus, n, hp_final, best_hx)
    forecast = {
        "bulan_target": str(nxt["ds"].iloc[0].date()),
        "Naive": float(last["harga_beras"]),
        "Prophet-only (tuned)": float(prophet_predict(p_final, nxt)[0]),
        "XGBoost-only (tuned)": float(predict_xgb_only(x_final, nxt, best_x)[0]),
        "Hybrid (tuned)": h_pred,
    }
    if SMOKE:
        print("SMOKE OK", forecast)
        return
    joblib.dump(p_final, os.path.join(SCRIPT_DIR, "final_prophet.pkl"))
    joblib.dump(x_final, os.path.join(SCRIPT_DIR, "final_xgboost.pkl"))
    joblib.dump(hp_final, os.path.join(SCRIPT_DIR, "final_hybrid_prophet.pkl"))
    joblib.dump(hx_final, os.path.join(SCRIPT_DIR, "final_hybrid_xgboost.pkl"))

    final_cfg = {
        "scheme": "realistis: fitur bulan T -> harga bulan T+1",
        "prophet_tuned": best_p, "xgboost_only_tuned": best_x,
        "xgboost_only_features": xgb_feats(best_x),
        "hybrid_prophet_tuned": best_hp, "hybrid_xgboost_tuned": best_hx,
        "hybrid_xgboost_features": hybrid_feats(best_hx),
        "defaults": {"prophet": PROPHET_DEFAULT, "xgboost_only": XGB_ONLY_DEFAULT,
                     "hybrid_xgboost": HYB_XGB_DEFAULT},
    }
    with open(os.path.join(SCRIPT_DIR, "final_config.json"), "w") as f:
        json.dump(final_cfg, f, indent=4, default=_json_default)
    with open(os.path.join(SCRIPT_DIR, "results.json"), "w") as f:
        json.dump({"protocol": {"target_start": TARGET_START,
                                "validation": [VAL_START, VAL_END],
                                "test": [str(frame.loc[test_idx[0], 'ds'].date()),
                                         str(frame.loc[test_idx[-1], 'ds'].date())],
                                "n_val": len(val_idx), "n_test": len(test_idx),
                                "refit": "setiap bulan (expanding window)"},
                   "config": final_cfg, "results": results,
                   "forecast_next_month": forecast,
                   "runtime_sec": time.time() - t0},
                  f, indent=4, default=_json_default)

    print("Prakiraan", forecast)
    print(f"\nSelesai dalam {time.time() - t0:.0f} detik.")


def _val_prophet(frame, cfg, targets):
    for n in ("cmdstanpy", "prophet"):
        logging.getLogger(n).setLevel(logging.ERROR)
    return eval_prophet(frame, cfg, targets)


def _save(df, name):
    if not SMOKE:
        df.to_csv(os.path.join(SCRIPT_DIR, name), index=False)


def _row_to_cfg(row, template, prefix=""):
    cfg = {}
    for k, default in template.items():
        v = row[prefix + k]
        if v is None or (isinstance(v, float) and np.isnan(v)):
            v = None
        elif isinstance(default, bool):
            v = bool(v)
        elif isinstance(default, int) and not isinstance(default, bool):
            v = int(v)
        elif isinstance(default, float):
            v = float(v)
        cfg[k] = v
    if cfg.get("use_exog") and cfg.get("reg_prior_scale", 1) is None:
        cfg["reg_prior_scale"] = 10.0
    return cfg


def _json_default(o):
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.floating,)):
        return float(o)
    if isinstance(o, (np.bool_,)):
        return bool(o)
    return str(o)


if __name__ == "__main__":
    main()
