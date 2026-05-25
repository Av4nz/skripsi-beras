from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Union
import datetime

class ExternalFeatures(BaseModel):
    harga_gkg: float
    curah_hujan: float
    produksi_padi: float
    inflasi_pangan: float
    lebaran: int = Field(default=0, description="1 if Eid al-Fitr falls in this month, else 0")

class PredictionRequest(BaseModel):
    period: int = Field(default=1, description="Number of steps to forecast")
    external_features: Optional[ExternalFeatures] = Field(default=None, description="Provide to override historical data")

class TimeSeriesPoint(BaseModel):
    date: datetime.date
    value: float
    type: str = Field(description="'actual' or 'forecast'")

class StepDetail(BaseModel):
    step: int
    date: datetime.date
    yhat: float
    residual: float
    final_prediction: float
    features_used: Dict[str, float]

class PredictionDetails(BaseModel):
    steps: List[StepDetail]

class PredictionResponse(BaseModel):
    prediction: Union[float, List[float]]
    series: List[TimeSeriesPoint]
    details: PredictionDetails

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

class PrediksiSchema(BaseModel):
    id: int
    date: datetime.date
    result: float
    residual: Optional[float] = None
    model: str

    class Config:
        from_attributes = True

class MetricsSchema(BaseModel):
    model: str
    mae: float
    mape: float
    rmse: float

    class Config:
        from_attributes = True

class SavePredictionRequest(BaseModel):
    date: datetime.date
    result: float
    residual: Optional[float] = None
    model: str = "hybrid"
