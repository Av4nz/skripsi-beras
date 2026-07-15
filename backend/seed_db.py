"""
Seed database untuk sistem prediksi harga beras (arsitektur SKENARIO:
Prophet + regressor eksternal + XGBoost residual).

Mengisi ulang:
  1. Tabel `harga_beras` dari dataset terbaru
     (data_train/datasets/data_app/harga_beras_2018_2026.csv), difilter mulai
     2021 agar konsisten dengan periode pelatihan model & skripsi (rezim harga
     2018-2020 tidak dipakai dalam pemodelan).
  2. Tabel `metrics` dari hasil evaluasi model final
     (data_train/hybrid_model/trainv2/metrics_final_scenario.json):
        - prophet : Prophet + regressor eksternal (base)
        - hybrid  : Prophet + regressor eksternal + koreksi residual XGBoost

Jalankan (dari folder backend, dgn venv):
    .venv/Scripts/python.exe seed_db.py
"""

import os
import json

import pandas as pd

from app.core.database import SessionLocal, engine, Base
from app.models.db_models import HargaBeras, Metrics

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CSV_PATH = os.path.join(BASE_DIR, "data", "harga_beras_2018_2026.csv")
METRICS_JSON = os.path.join(BASE_DIR, "data", "metrics_final_scenario.json")
START_YEAR = 2021  # 2018-2020 tidak dipakai dalam pemodelan


def _f(v):
    """float atau None (untuk NaN)."""
    return float(v) if pd.notnull(v) else None


def seed():
    if not os.path.exists(CSV_PATH):
        print(f"[X] CSV tidak ditemukan: {CSV_PATH}")
        return

    # pastikan tabel ada (skema tidak berubah)
    Base.metadata.create_all(bind=engine)

    df = pd.read_csv(CSV_PATH)
    df["tanggal"] = pd.to_datetime(df["tanggal"])
    df = df[df["tanggal"].dt.year >= START_YEAR].sort_values("tanggal").reset_index(drop=True)

    db = SessionLocal()
    try:
        # ---------- 1. harga_beras ----------
        deleted = db.query(HargaBeras).delete()
        db.commit()
        print(f"harga_beras: {deleted} baris lama dihapus.")

        records = [
            HargaBeras(
                date=row["tanggal"].date(),
                price=float(row["harga_beras"]),
                lebaran=int(row["lebaran"]) if pd.notnull(row["lebaran"]) else 0,
                harga_gkg=_f(row["harga_gkg"]),
                curah_hujan=_f(row["curah_hujan"]),
                produksi_padi=_f(row["produksi_padi"]),
                inflasi_pangan=_f(row["inflasi_pangan"]),
            )
            for _, row in df.iterrows()
        ]
        db.add_all(records)
        db.commit()
        print(f"harga_beras: {len(records)} baris baru dimasukkan "
              f"({df['tanggal'].min().date()} .. {df['tanggal'].max().date()}).")

        # ---------- 2. metrics ----------
        db.query(Metrics).delete()
        db.commit()

        if os.path.exists(METRICS_JSON):
            with open(METRICS_JSON) as f:
                agg = json.load(f)["backtest_aggregate"]
            metrics = [
                Metrics(model="prophet",
                        mae=round(agg["base_mae"], 2),
                        mape=round(agg["base"] * 100, 2),
                        rmse=round(agg["base_rmse"], 2)),
                Metrics(model="hybrid",
                        mae=round(agg["hybrid_mae"], 2),
                        mape=round(agg["hybrid"] * 100, 2),
                        rmse=round(agg["hybrid_rmse"], 2)),
            ]
            src = "metrics_final_scenario.json (rolling backtest 2024-2026)"
        else:
            # fallback bila JSON belum tersedia
            metrics = [
                Metrics(model="prophet", mae=425.0, mape=2.92, rmse=636.0),
                Metrics(model="hybrid", mae=426.3, mape=2.93, rmse=637.0),
            ]
            src = "fallback (JSON tidak ditemukan)"
        db.add_all(metrics)
        db.commit()
        print(f"metrics: {len(metrics)} baris dimasukkan dari {src}:")
        for m in metrics:
            print(f"   - {m.model:<8} MAE={m.mae}  MAPE={m.mape}%  RMSE={m.rmse}")

        print("\n[OK] Seeding selesai.")
    except Exception as e:
        db.rollback()
        print(f"[X] Gagal seeding: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed()
