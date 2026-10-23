from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Union
import datetime

class TimeSeriesPoint(BaseModel):
    date: datetime.date
    value: float
    type: str = Field(description="'actual' or 'forecast'")

class DecompositionComponent(BaseModel):
    name: str
    label: str
    contribution: float = Field(description="Estimated contribution to the prediction, in Rupiah")

class PredictionDecomposition(BaseModel):
    trend: float = Field(description="Baseline trend value in Rupiah")
    components: List[DecompositionComponent]

class HargaBerasSchema(BaseModel):
    date: datetime.date
    price: float
    lebaran: int
    harga_gkg: Optional[float] = None
    curah_hujan: Optional[float] = None
    produksi_padi: Optional[float] = None
    inflasi_pangan: Optional[float] = None

    class Config:
        from_attributes = True

# ---------------------------------------------------------------------------
# API "Beras": per jenis, tanpa masukan faktor eksternal
# ---------------------------------------------------------------------------
class HargaJenisPoint(BaseModel):
    date: datetime.date
    price: float


class RiceStep(BaseModel):
    step: int
    date: datetime.date
    hybrid: float = Field(description="Prediksi hybrid (Prophet + koreksi residual XGBoost), Rp/kg")
    prophet: float
    residual: float
    naive: float = Field(description="Pembanding: harga bulan terakhir dipertahankan")
    arima: float = Field(description="Pembanding: ARIMA(1,1,0)")
    decomposition: Optional[PredictionDecomposition] = None


class RicePredictionResponse(BaseModel):
    jenis: str
    horizon: int
    origin_date: datetime.date = Field(description="Bulan terakhir pada riwayat harga, titik awal prediksi")
    origin_price: float
    steps: List[RiceStep]
    series: List[TimeSeriesPoint]


class RiceMetricRow(BaseModel):
    horizon: int
    model: str
    n_uji: int
    mape: float
    mae: float
    rmse: float


class RiceMetricsResponse(BaseModel):
    jenis: str
    protokol: str
    metrik: List[RiceMetricRow]
