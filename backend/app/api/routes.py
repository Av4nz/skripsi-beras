from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.core.database import get_db
from app.models import db_models
from app.schemas import schemas
from app.services.predictor import predict_hybrid

router = APIRouter()

@router.post("/predict", response_model=schemas.PredictionResponse)
def run_prediction(request: schemas.PredictionRequest, db: Session = Depends(get_db)):
    try:
        result = predict_hybrid(db, request)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/data/historical", response_model=List[schemas.HargaBerasSchema])
def get_historical_data(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    records = db.query(db_models.HargaBeras).order_by(db_models.HargaBeras.date.desc()).offset(skip).limit(limit).all()
    return records

@router.get("/data/predictions", response_model=List[schemas.PrediksiSchema])
def get_saved_predictions(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    records = db.query(db_models.Prediksi).order_by(db_models.Prediksi.date.desc()).offset(skip).limit(limit).all()
    return records

@router.get("/metrics", response_model=List[schemas.MetricsSchema])
def get_metrics(db: Session = Depends(get_db)):
    records = db.query(db_models.Metrics).all()
    return records

@router.post("/predictions/save", response_model=schemas.PrediksiSchema)
def save_prediction(request: schemas.SavePredictionRequest, db: Session = Depends(get_db)):
    new_prediction = db_models.Prediksi(
        date=request.date,
        result=request.result,
        residual=request.residual,
        model=request.model
    )
    db.add(new_prediction)
    try:
        db.commit()
        db.refresh(new_prediction)
        return new_prediction
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Failed to save prediction: {str(e)}")
