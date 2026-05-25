import pandas as pd
from app.core.database import SessionLocal, engine
from app.models.db_models import HargaBeras, Metrics
import os

def seed_real_data():
    csv_path = "data_train/hybrid_model/harga_beras_2021_2025.csv"
    
    if not os.path.exists(csv_path):
        print(f"❌ Cannot find {csv_path}")
        return

    print(f"Reading data from {csv_path}...")
    df = pd.read_csv(csv_path)
    
    db = SessionLocal()
    try:
        # Since we added a new column (lebaran), it's easiest to drop and recreate the tables
        # from app.core.database import Base, engine
        # print("Dropping old tables and recreating them with the new schema...")
        # Base.metadata.drop_all(bind=engine)
        # Base.metadata.create_all(bind=engine)
        # print("Tables recreated.")
        
        # Insert real data
        # records_to_insert = []
        # for index, row in df.iterrows():
        #     record = HargaBeras(
        #         date=pd.to_datetime(row['tanggal']).date(),
        #         price=float(row['harga_beras']),
        #         lebaran=int(row['lebaran']),
        #         harga_gkg=float(row['harga_gkg']) if pd.notnull(row['harga_gkg']) else None,
        #         curah_hujan=float(row['curah_hujan']) if pd.notnull(row['curah_hujan']) else None,
        #         produksi_padi=float(row['produksi_padi']) if pd.notnull(row['produksi_padi']) else None,
        #         inflasi_pangan=float(row['inflasi_pangan']) if pd.notnull(row['inflasi_pangan']) else None
        #     )
        #     records_to_insert.append(record)
            
        # db.add_all(records_to_insert)
        # db.commit()
        
        # print(f"✅ Successfully inserted {len(records_to_insert)} real historical records into the database!")
        
        # Seed model metrics (from time_series_training.ipynb)
        metrics_to_insert = [
            Metrics(model="prophet",      mae=423.71, mape=2.99, rmse=462.15),
            Metrics(model="hybrid",       mae=409.65, mape=2.89, rmse=450.12),
            Metrics(model="hybrid_tuned", mae=391.86, mape=2.77, rmse=442.65),
        ]
        db.add_all(metrics_to_insert)
        db.commit()
        print("✅ Successfully inserted 3 model metrics (Prophet, Hybrid, Hybrid Tuned)!")
        
    except Exception as e:
        db.rollback()
        print(f"❌ Failed to insert data: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    seed_real_data()
