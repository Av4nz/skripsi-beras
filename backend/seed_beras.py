"""
Seed tabel `harga_beras_jenis` dari backend/data/harga_beras_per_jenis_2021_2026.csv.

PENGAMAN: skrip ini hanya mengubah tabel baru `harga_beras_jenis` (tabel lama tidak disentuh), dan menolak
berjalan ke basis data selain SQLite lokal kecuali variabel lingkungan KONFIRMASI_PRODUKSI=ya diset.

Uji lokal:
    set DATABASE_URL=sqlite:///./uji_beras.db
    .venv/Scripts/python.exe seed_beras.py
"""
import os
import sys

import pandas as pd

from app.core.database import SessionLocal, engine, Base, DATABASE_URL
from app.models.db_models import HargaBerasJenis

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CSV_PATH = os.path.join(BASE_DIR, "data", "harga_beras_per_jenis_2021_2026.csv")


def seed():
    lokal = DATABASE_URL.startswith("sqlite")
    if not lokal and os.environ.get("KONFIRMASI_PRODUKSI") != "ya":
        print("[X] DATABASE_URL bukan SQLite lokal. Set KONFIRMASI_PRODUKSI=ya bila memang sengaja menulis ke sana.")
        sys.exit(2)
    Base.metadata.create_all(bind=engine)
    df = pd.read_csv(CSV_PATH, index_col=0)
    df.index = pd.to_datetime(df.index + "-01")
    db = SessionLocal()
    try:
        hapus = db.query(HargaBerasJenis).delete()
        db.commit()
        rows = [HargaBerasJenis(jenis=j, date=d.date(), price=float(v))
                for j in df.columns for d, v in df[j].items() if pd.notnull(v)]
        db.add_all(rows)
        db.commit()
        print(f"harga_beras_jenis: {hapus} baris lama dihapus, {len(rows)} baris baru "
              f"({df.index.min().date()} .. {df.index.max().date()}, {len(df.columns)} jenis).")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed()
