from sqlalchemy import Column, Integer, String, Float, Date, DateTime
from app.core.database import Base
import datetime

class HargaBeras(Base):
    __tablename__ = "harga_beras"

    id = Column(Integer, primary_key=True, index=True)
    date = Column(Date, unique=True, index=True, nullable=False)
    price = Column(Float, nullable=False)
    lebaran = Column(Integer, default=0)
    harga_gkg = Column(Float, nullable=True)
    curah_hujan = Column(Float, nullable=True)
    produksi_padi = Column(Float, nullable=True)
    inflasi_pangan = Column(Float, nullable=True)

class Metrics(Base):
    __tablename__ = "metrics"

    id = Column(Integer, primary_key=True, index=True)
    model = Column(String, unique=True, index=True, nullable=False)
    mae = Column(Float, nullable=False)
    mape = Column(Float, nullable=False)
    rmse = Column(Float, nullable=True)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
