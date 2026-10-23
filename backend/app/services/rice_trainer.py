"""
Pelatihan ulang model beras di dalam backend (tanpa berkas), dari harga bulanan di basis data.

Logika sama dengan training/.../trainv5_sistem/train_final_beras.py: per jenis, Prophet (tren + musiman tahunan)
lalu XGBoost untuk residual. Hyperparameter diambil dari config.json artefak (dibekukan dari trainv3).

Hasil latih disimpan di memori (rice_predictor.set_rice_models). Berkas Space tidak permanen, jadi saat start
backend memuat .pkl bawaan lalu melatih ulang di latar belakang bila basis data lebih baru dari model.
"""
import logging
import threading
import warnings
from datetime import datetime, timezone
from typing import Dict, Tuple

import numpy as np
import pandas as pd
from prophet import Prophet
from xgboost import XGBRegressor

from app.services import rice_predictor as rp

warnings.filterwarnings("ignore")
logging.getLogger("cmdstanpy").setLevel(logging.ERROR)
logging.getLogger("prophet").setLevel(logging.ERROR)
log = logging.getLogger("rice_trainer")

_kunci_latih = threading.Lock()


def phi_cls(series) -> float:
    d = np.diff(np.asarray(series, float))
    return float(np.sum(d[1:] * d[:-1]) / np.sum(d[:-1] ** 2))


def latih(series_per_jenis: Dict[str, pd.Series], cfg_base: dict) -> Tuple[dict, dict]:
    """Latih satu pasang Prophet + XGBoost per jenis. Mengembalikan (config, models) baru."""
    pc, xp = cfg_base["prophet"], cfg_base["xgb"]
    keys = cfg_base["fitur_xgb"]
    cfg = {k: v for k, v in cfg_base.items() if k != "jenis"}
    cfg["jenis"], models = {}, {}
    awal, akhir = [], []
    for jenis, meta in cfg_base["jenis"].items():
        s = series_per_jenis[jenis].astype(float).sort_index()
        m = Prophet(yearly_seasonality=int(pc["yearly_order"]), weekly_seasonality=False, daily_seasonality=False,
                    changepoint_prior_scale=pc["changepoint_prior_scale"],
                    seasonality_prior_scale=pc["seasonality_prior_scale"], seasonality_mode=pc["seasonality_mode"])
        train = pd.DataFrame({"ds": s.index, "y": s.values})
        m.fit(train)
        in_s = m.predict(train[["ds"]])["yhat"].values
        resid = list(s.values - in_s)
        rows, ys = [], []
        for i in range(3, len(s)):
            rows.append(rp._row(s.values[:i], resid[:i], s.index[i], cfg_base).iloc[0].to_dict())
            ys.append(resid[i])
        xg = XGBRegressor(random_state=42, n_jobs=1, **xp).fit(pd.DataFrame(rows)[keys], ys)
        models[jenis] = {"prophet": m, "xgb": xg}
        cfg["jenis"][jenis] = {"slug": meta["slug"], "phi": phi_cls(s.values), "harga_terakhir": float(s.iloc[-1]),
                               "bulan_terakhir": str(s.index[-1].date())}
        awal.append(s.index.min()); akhir.append(s.index.max())
    cfg["data_awal"] = str(min(awal).date())
    cfg["data_akhir"] = str(max(akhir).date())
    cfg["jumlah_bulan"] = int(max(len(series_per_jenis[j]) for j in cfg_base["jenis"]))
    cfg["cutoff"] = None
    cfg["dilatih_pada"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    return cfg, models


def baca_series_db(db) -> Dict[str, pd.Series]:
    from app.models.db_models import HargaBerasJenis
    out = {}
    for jenis in rp.list_rice_types():
        rows = (db.query(HargaBerasJenis).filter(HargaBerasJenis.jenis == jenis)
                .order_by(HargaBerasJenis.date.asc()).all())
        out[jenis] = pd.Series([r.price for r in rows], index=pd.to_datetime([r.date for r in rows]))
    return out


def sinkron_dari_db(db, paksa: bool = False) -> bool:
    """Latih ulang bila data di DB lebih baru dari model yang termuat. True bila model diganti."""
    cfg_base = rp.get_config()
    if cfg_base is None:
        return False
    with _kunci_latih:
        series = baca_series_db(db)
        if any(len(s) < 6 for s in series.values()):
            log.warning("Riwayat DB belum cukup untuk melatih ulang.")
            return False
        terbaru = max(s.index.max() for s in series.values())
        if not paksa and terbaru <= pd.Timestamp(cfg_base["data_akhir"]):
            return False
        cfg, models = latih(series, cfg_base)
        rp.set_rice_models(cfg, models)
        log.info("Model beras dilatih ulang sampai %s", cfg["data_akhir"])
        return True


def sinkron_saat_start() -> None:
    """Dipanggil saat startup. Berjalan di thread terpisah supaya health check tidak tertahan."""
    def _kerja():
        from app.core.database import SessionLocal
        db = SessionLocal()
        try:
            sinkron_dari_db(db)
        except Exception:
            log.exception("Sinkron model saat start gagal; model bawaan tetap dipakai.")
        finally:
            db.close()
    threading.Thread(target=_kerja, name="sinkron-model", daemon=True).start()
