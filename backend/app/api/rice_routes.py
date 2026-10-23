"""
Endpoint "Beras": per jenis beras, tanpa masukan faktor eksternal.
Ditambahkan di samping endpoint lama (/predict, /data/historical, /metrics) tanpa mengubahnya.
"""
import json
import os
from typing import List

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models import db_models
from app.schemas import schemas
from app.services import rice_predictor as rp

router = APIRouter(prefix="/beras", tags=["beras"])

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
METRIK_PATH = os.path.abspath(os.path.join(BASE_DIR, "../../data/metrik_beras.json"))
_metrik_cache = {}


def _metrik():
    if not _metrik_cache:
        with open(METRIK_PATH, encoding="utf-8") as f:
            _metrik_cache.update(json.load(f))
    return _metrik_cache


def _cek_jenis(jenis: str) -> str:
    if jenis not in rp.list_rice_types():
        raise HTTPException(status_code=404, detail=f"Jenis beras tidak dikenal: {jenis}")
    return jenis


@router.get("/jenis", response_model=List[str])
def daftar_jenis():
    return rp.list_rice_types()


@router.get("/historis", response_model=List[schemas.HargaJenisPoint])
def historis(jenis: str = Query(...), limit: int = Query(120, ge=1, le=240), db: Session = Depends(get_db)):
    _cek_jenis(jenis)
    rows = (db.query(db_models.HargaBerasJenis)
            .filter(db_models.HargaBerasJenis.jenis == jenis)
            .order_by(db_models.HargaBerasJenis.date.desc()).limit(limit).all())
    return [schemas.HargaJenisPoint(date=r.date, price=r.price) for r in reversed(rows)]


@router.get("/prediksi", response_model=schemas.RicePredictionResponse)
def prediksi(jenis: str = Query(...), horizon: int = Query(1, ge=1, le=rp.MAX_HORIZON), db: Session = Depends(get_db)):
    _cek_jenis(jenis)
    rows = (db.query(db_models.HargaBerasJenis)
            .filter(db_models.HargaBerasJenis.jenis == jenis)
            .order_by(db_models.HargaBerasJenis.date.asc()).all())
    if len(rows) < 6:
        raise HTTPException(status_code=422, detail="Riwayat harga jenis ini belum cukup.")
    hist = pd.Series([r.price for r in rows], index=pd.to_datetime([r.date for r in rows]))
    try:
        res = rp.predict_rice(jenis, hist, horizon)
    except rp.RiceModelError as e:
        raise HTTPException(status_code=422, detail=str(e))
    origin = hist.index[-1].date()
    steps = [schemas.RiceStep(step=r.step, date=r.date.date(), hybrid=r.hybrid, prophet=r.prophet, residual=r.residual,
                              naive=r.naive, arima=r.arima, decomposition=r.decomposition) for r in res]
    series = [schemas.TimeSeriesPoint(date=d.date(), value=float(v), type="actual") for d, v in hist.iloc[-24:].items()]
    series += [schemas.TimeSeriesPoint(date=s.date, value=s.hybrid, type="forecast") for s in steps]
    return schemas.RicePredictionResponse(jenis=jenis, horizon=horizon, origin_date=origin,
                                          origin_price=float(hist.iloc[-1]), steps=steps, series=series)


@router.get("/info")
def info(db: Session = Depends(get_db)):
    """Keadaan data dan model: untuk menampilkan seberapa baru data yang dipakai."""
    cfg = rp.get_config() or {}
    terakhir = db.query(func.max(db_models.HargaBerasJenis.date)).scalar()
    return {"data_terakhir": str(terakhir) if terakhir else None, "model_data_akhir": cfg.get("data_akhir"),
            "model_dilatih_pada": cfg.get("dilatih_pada"), "jumlah_bulan_model": cfg.get("jumlah_bulan")}


@router.get("/metrik", response_model=schemas.RiceMetricsResponse)
def metrik(jenis: str = Query(...)):
    _cek_jenis(jenis)
    m = _metrik()
    return schemas.RiceMetricsResponse(jenis=jenis, protokol=m["protokol"],
                                       metrik=[schemas.RiceMetricRow(**r) for r in m["metrik"][jenis]])
