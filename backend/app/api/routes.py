from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.core.database import get_db
from app.models import db_models
from app.schemas import schemas

router = APIRouter()

@router.get("/data/historical", response_model=List[schemas.HargaBerasSchema])
def get_historical_data(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    records = db.query(db_models.HargaBeras).order_by(db_models.HargaBeras.date.desc()).offset(skip).limit(limit).all()
    return records
