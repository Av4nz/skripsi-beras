"""
Uji API beras terhadap SQLite lokal (BUKAN produksi). URL basis data dipaksa ke SQLite sebelum impor aplikasi.
Server uvicorn dijalankan di port bebas pada localhost, lalu diuji lewat HTTP nyata.

Jalankan dari folder backend dengan venv backend:
    .venv\\Scripts\\python.exe uji_api_beras.py
"""
import os, sys, logging, warnings, time, threading, socket
warnings.filterwarnings("ignore")
logging.getLogger("cmdstanpy").setLevel(logging.ERROR); logging.getLogger("prophet").setLevel(logging.ERROR)
sys.stdout.reconfigure(encoding="utf-8")

DB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "uji_beras.db")
if os.path.exists(DB):
    os.remove(DB)
os.environ["DATABASE_URL"] = "sqlite:///" + DB.replace("\\", "/")   # dipaksa SEBELUM impor app (load_dotenv tidak menimpa)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.core.database import DATABASE_URL
assert DATABASE_URL.startswith("sqlite"), "basis data bukan SQLite, uji dihentikan"
import seed_beras
seed_beras.seed()

import requests, uvicorn
from app.main import app


def port_bebas():
    s = socket.socket(); s.bind(("127.0.0.1", 0)); p = s.getsockname()[1]; s.close(); return p


PORT = port_bebas()
BASE = f"http://127.0.0.1:{PORT}"
server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=PORT, log_level="error"))
threading.Thread(target=server.run, daemon=True).start()
for _ in range(120):
    try:
        requests.get(BASE + "/", timeout=1); break
    except Exception:
        time.sleep(0.5)


class C:
    def get(self, path, params=None):
        return requests.get(BASE + path, params=params, timeout=120)


c = C()
hasil = []
def cek(nama, ok, info=""):
    hasil.append(bool(ok)); print(("LULUS " if ok else "GAGAL ") + nama + (" | " + str(info) if info else ""))

r = c.get("/"); cek("health check", r.status_code == 200)
r = c.get("/beras/jenis"); jenis = r.json()
cek("daftar 6 jenis", r.status_code == 200 and len(jenis) == 6, jenis)
for j in jenis:
    t0 = time.time()
    r = c.get("/beras/prediksi", params={"jenis": j, "horizon": 1}); d = r.json()
    ok = (r.status_code == 200 and d["origin_date"] == "2026-05-01" and len(d["steps"]) == 1
          and d["steps"][0]["date"] == "2026-06-01" and d["steps"][0]["hybrid"] > 0)
    info = (f'{d["steps"][0]["hybrid"]:.0f} (naive {d["steps"][0]["naive"]:.0f}, arima {d["steps"][0]["arima"]:.0f}) {time.time()-t0:.2f}s'
            if ok else r.text[:150])
    cek(f"prediksi 1 bulan {j}", ok, info)
r = c.get("/beras/prediksi", params={"jenis": "Medium II", "horizon": 6}); d = r.json()
cek("horizon 6: 6 langkah, Juni sampai November 2026",
    r.status_code == 200 and [s["date"] for s in d["steps"]] == ["2026-06-01", "2026-07-01", "2026-08-01", "2026-09-01", "2026-10-01", "2026-11-01"])
cek("seri memuat titik aktual dan forecast", {x["type"] for x in d["series"]} == {"actual", "forecast"})
cek("naive konstan sama dengan harga terakhir", all(abs(s["naive"] - d["origin_price"]) < 1e-9 for s in d["steps"]), d["origin_price"])
comp = [x["name"] for x in d["steps"][0]["decomposition"]["components"]] if d["steps"][0]["decomposition"] else None
cek("dekomposisi: hanya musiman dan Lebaran (tanpa faktor eksternal)", comp is not None and set(comp) == {"yearly", "lebaran"}, comp)
cek("hybrid = prophet + residual (selisih < 0,01)", all(abs(s["hybrid"] - s["prophet"] - s["residual"]) < 0.01 for s in d["steps"]))
cek("horizon 0 ditolak 422", c.get("/beras/prediksi", params={"jenis": "Medium II", "horizon": 0}).status_code == 422)
cek("horizon 7 ditolak 422", c.get("/beras/prediksi", params={"jenis": "Medium II", "horizon": 7}).status_code == 422)
cek("horizon bukan angka ditolak 422", c.get("/beras/prediksi", params={"jenis": "Medium II", "horizon": "abc"}).status_code == 422)
cek("jenis tidak dikenal 404", c.get("/beras/prediksi", params={"jenis": "Pandan Wangi", "horizon": 1}).status_code == 404)
cek("jenis kosong ditolak 422", c.get("/beras/prediksi", params={"horizon": 1}).status_code == 422)
a = c.get("/beras/prediksi", params={"jenis": "Medium II", "horizon": 1}).json()["steps"][0]["hybrid"]
b = c.get("/beras/prediksi", params={"jenis": "Medium II", "horizon": 1, "harga_gkg": 99999}).json()["steps"][0]["hybrid"]
cek("parameter faktor eksternal diabaikan (hasil sama)", a == b, (a, b))
r = c.get("/beras/historis", params={"jenis": "Super I", "limit": 12}); h = r.json()
cek("historis 12 bulan urut naik, berakhir Mei 2026",
    r.status_code == 200 and len(h) == 12 and h[-1]["date"] == "2026-05-01" and h == sorted(h, key=lambda x: x["date"]))
cek("historis jenis tidak dikenal 404", c.get("/beras/historis", params={"jenis": "X"}).status_code == 404)
r = c.get("/beras/metrik", params={"jenis": "Medium II"}); m = r.json()
baris = {(x["horizon"], x["model"]): x for x in m["metrik"]}
cek("metrik 24 baris (6 horizon x 4 model)", r.status_code == 200 and len(m["metrik"]) == 24)
cek("metrik h=1 Medium II: naive 0,834 dan hybrid 2,532",
    baris[(1, "naive")]["mape"] == 0.834 and baris[(1, "hybrid")]["mape"] == 2.532,
    (baris[(1, "naive")]["mape"], baris[(1, "hybrid")]["mape"]))
cek("endpoint lama /metrics dan /predict sudah dihapus (404/405)", c.get("/metrics").status_code == 404 and c.get("/predict").status_code in (404, 405))
cek("/data/historical (faktor sebagai informasi) tetap ada", c.get("/data/historical").status_code == 200)

print(f"\n{sum(hasil)}/{len(hasil)} lulus")
server.should_exit = True
time.sleep(1)
try:
    os.remove(DB)
except Exception:
    pass
sys.exit(0 if all(hasil) else 1)
