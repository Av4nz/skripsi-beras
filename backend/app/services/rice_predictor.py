"""
Prediksi harga beras per jenis (hybrid Prophet + XGBoost, skema realistis).

Tanpa faktor eksternal, tanpa penanda Lebaran, dan tanpa masukan faktor dari pengguna. Masukan hanya:
  - jenis beras
  - horizon (bulan)
Titik awal prediksi adalah bulan terakhir yang tersedia pada riwayat harga jenis itu
(bukan bulan yang dipatok). Pembanding: naive dan ARIMA(1,1,0) (AR(1) pada selisih).

Modul ini tidak mengimpor FastAPI maupun SQLAlchemy supaya dapat diuji terpisah.
"""
import json
import os
from dataclasses import dataclass
from typing import Dict, List, Optional

import joblib
import numpy as np
import pandas as pd

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.abspath(os.path.join(BASE_DIR, "../../"))
ARTIFACT_DIR = os.path.join(ROOT_DIR, "ml_models", "beras")

MAX_HORIZON = 6   # uji horizon 1 sampai 6 bulan; galat membesar seiring horizon

_state: Dict = {"config": None, "models": {}}


class RiceModelError(ValueError):
    pass


def load_rice_models(artifact_dir: Optional[str] = None) -> None:
    d = artifact_dir or ARTIFACT_DIR
    path = os.path.join(d, "config.json")
    if not os.path.exists(path):
        raise RiceModelError(f"config.json tidak ditemukan di {d}")
    with open(path, encoding="utf-8") as f:
        cfg = json.load(f)
    models = {}
    for jenis, meta in cfg["jenis"].items():
        sub = os.path.join(d, meta["slug"])
        models[jenis] = {
            "prophet": joblib.load(os.path.join(sub, "prophet.pkl")),
            "xgb": joblib.load(os.path.join(sub, "xgb.pkl")),
        }
    _state["config"], _state["models"] = cfg, models


def list_rice_types() -> List[str]:
    cfg = _state["config"]
    return list(cfg["jenis"].keys()) if cfg else []


def _row(prices, resid, date, cfg) -> pd.DataFrame:
    p = list(prices)
    r = {
        "resid_lag1": resid[-1], "resid_lag2": resid[-2],
        "price_t": p[-1], "price_t1": p[-2], "price_t2": p[-3],
        "rolling_mean_3": float(np.mean(p[-3:])), "diff_t": p[-1] - p[-2],
        "month_sin": float(np.sin(2 * np.pi * date.month / 12)),
        "month_cos": float(np.cos(2 * np.pi * date.month / 12)),
    }
    return pd.DataFrame([r])[cfg["fitur_xgb"]]


@dataclass
class StepResult:
    step: int
    date: pd.Timestamp
    prophet: float
    residual: float
    hybrid: float
    naive: float
    arima: float
    decomposition: Optional[dict]


def predict_rice(jenis: str, history: pd.Series, horizon: int) -> List[StepResult]:
    """
    history: harga bulanan (indeks tanggal awal bulan, urut naik) untuk satu jenis.
    Prediksi dimulai dari bulan terakhir pada history.
    """
    cfg = _state["config"]
    if cfg is None:
        raise RiceModelError("Model belum dimuat.")
    if jenis not in _state["models"]:
        raise RiceModelError(f"Jenis beras tidak dikenal: {jenis}")
    if not (1 <= horizon <= MAX_HORIZON):
        raise RiceModelError(f"Horizon harus 1 sampai {MAX_HORIZON} bulan.")
    s = history.astype(float).sort_index()
    if len(s) < 6:
        raise RiceModelError("Riwayat harga kurang dari 6 bulan.")

    prophet, xgb = _state["models"][jenis]["prophet"], _state["models"][jenis]["xgb"]
    phi = cfg["jenis"][jenis]["phi"]
    last_date = s.index[-1]
    targets = [last_date + pd.DateOffset(months=h) for h in range(1, horizon + 1)]

    # residual in-sample pada riwayat (dipakai sebagai lag residual awal)
    hist_df = pd.DataFrame({"ds": s.index})
    in_s = prophet.predict(hist_df)["yhat"].values
    resid = list(s.values - in_s)

    fut_df = pd.DataFrame({"ds": targets})
    fut = prophet.predict(fut_df)

    prices = list(s.values)
    last_price, last_diff = float(s.iloc[-1]), float(s.iloc[-1] - s.iloc[-2])
    out, arima_price, arima_diff = [], last_price, last_diff
    for i, t in enumerate(targets):
        yhat = float(fut.loc[i, "yhat"])
        r_hat = float(xgb.predict(_row(prices, resid, t, cfg))[0])
        final = yhat + r_hat
        arima_diff = phi * arima_diff
        arima_price += arima_diff
        out.append(StepResult(
            step=i + 1, date=t, prophet=yhat, residual=r_hat, hybrid=final,
            naive=last_price, arima=arima_price,
            decomposition=_decompose(prophet, fut.iloc[[i]]),
        ))
        resid.append(r_hat)      # residual masa depan tidak diketahui: diisi koreksi terprediksi
        prices.append(final)
    return out


def _decompose(prophet, row_df):
    try:
        row = row_df.iloc[0]
        trend = float(row["trend"])
        comps = []
        for name, cfgc in getattr(prophet, "seasonalities", {}).items():
            if name in row_df.columns:
                v = float(row[name])
                comps.append({"name": name, "label": "Pola Musiman Tahunan" if name == "yearly" else name,
                              "contribution": trend * v if cfgc.get("mode") == "multiplicative" else v})
        return {"trend": trend, "components": comps}
    except Exception:
        return None
