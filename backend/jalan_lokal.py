"""
Jalankan backend lokal untuk mencoba sistem (BUKAN produksi).
Memakai SQLite sementara (lokal_tampilan.db, dibuat ulang tiap dijalankan) dan mengisinya dari CSV.

Dari folder backend:
    .venv\\Scripts\\python.exe jalan_lokal.py
API: http://127.0.0.1:8000  (dokumentasi: http://127.0.0.1:8000/docs)
"""
import os, sys, logging, warnings
warnings.filterwarnings("ignore")
logging.getLogger("cmdstanpy").setLevel(logging.ERROR)
logging.getLogger("prophet").setLevel(logging.ERROR)

DB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "lokal_tampilan.db")
if os.path.exists(DB):
    os.remove(DB)
os.environ["DATABASE_URL"] = "sqlite:///" + DB.replace("\\", "/")
os.environ["CORS_ORIGINS"] = "http://localhost:3000,http://localhost:3100"
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.core.database import DATABASE_URL
assert DATABASE_URL.startswith("sqlite"), "basis data bukan SQLite, dihentikan"
import seed_beras
seed_beras.seed()

import uvicorn
from app.main import app
uvicorn.run(app, host="127.0.0.1", port=8000, log_level="warning")
