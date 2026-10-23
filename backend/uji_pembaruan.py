"""
Uji pembaruan harga bulanan (SQLite lokal, BUKAN produksi).

Bagian A: sumber PIHPS dipalsukan (deterministik): bulan penuh, idempoten, bulan berjalan tidak masuk,
          sumber gagal, lonjakan harga, tabel kosong, token admin, pelatihan ulang, kesetaraan dengan train_final.
Bagian B (opsional, env UJI_NYATA=1): tarik BI sungguhan untuk Juni 2026 ke atas pada salinan data sampai Mei 2026.

Jalankan dari backend:  .venv\\Scripts\\python.exe uji_pembaruan.py
"""
import os, sys, logging, warnings, time, threading, socket
warnings.filterwarnings("ignore")
logging.getLogger("cmdstanpy").setLevel(logging.ERROR); logging.getLogger("prophet").setLevel(logging.ERROR)
sys.stdout.reconfigure(encoding="utf-8")

DB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "uji_pembaruan.db")
if os.path.exists(DB):
    os.remove(DB)
os.environ["DATABASE_URL"] = "sqlite:///" + DB.replace("\\", "/")
os.environ.pop("ADMIN_TOKEN", None)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.core.database import DATABASE_URL, SessionLocal
assert DATABASE_URL.startswith("sqlite")
import seed_beras
seed_beras.seed()

from datetime import date
import requests, uvicorn
from sqlalchemy import func
from app.models.db_models import HargaBerasJenis
from app.services import pihps_updater as pu, rice_predictor as rp, rice_trainer as rt
from app.main import app

hasil = []
def cek(nama, ok, info=""):
    hasil.append(bool(ok)); print(("LULUS " if ok else "GAGAL ") + nama + (" | " + str(info) if info else ""))

# ---------------- A. logika dengan sumber palsu ----------------
cek("bulan penuh setelah Mei 2026, sekarang 2026-10-23 (Juni-September)",
    [d.strftime("%Y-%m") for d in pu.bulan_penuh_setelah(date(2026, 5, 1), date(2026, 10, 23))] == ["2026-06", "2026-07", "2026-08", "2026-09"])
cek("Oktober belum penuh pada 2026-10-31 (jeda 2 hari)", date(2026, 10, 1) not in pu.bulan_penuh_setelah(date(2026, 9, 1), date(2026, 10, 31)))
cek("Oktober penuh pada 2026-11-02", date(2026, 10, 1) in pu.bulan_penuh_setelah(date(2026, 9, 1), date(2026, 11, 2)))
cek("pergantian tahun: Des 2026 setelah Nov", [d.strftime("%Y-%m") for d in pu.bulan_penuh_setelah(date(2026, 11, 1), date(2027, 1, 5))] == ["2026-12"])

asli = pu.ambil_harian
def palsu_ok(kode, tgl):
    return 10000.0 + int(kode[-1]) * 1000 + tgl.month * 10      # deterministik per jenis dan bulan
def palsu_lonjak(kode, tgl):
    return 20000.0 if (kode == "1_1" and tgl.month == 6) else palsu_ok(kode, tgl)   # Bawah I Juni melonjak sekitar 52%
pu.ambil_harian = palsu_lonjak
db = SessionLocal()
r = pu.perbarui(db, sekarang=date(2026, 8, 5))                    # penuh: Juni, Juli
cek("sumber palsu: menambah Juni dan Juli x 6 jenis", [x["bulan"] for x in r["ditambah"]] == ["2026-06", "2026-07"] and all(x["baris"] == 6 for x in r["ditambah"]), r["ditambah"])
cek("nilai = rata-rata harian yang diambil", db.query(HargaBerasJenis).filter_by(jenis="Medium II", date=date(2026, 7, 1)).one().price == 10000 + 4 * 1000 + 70)
cek("lonjakan > 20% dicatat sebagai peringatan, nilai TIDAK diubah",
    any("Bawah I" in w and "2026-06" in w for w in r["peringatan"]) and db.query(HargaBerasJenis).filter_by(jenis="Bawah I", date=date(2026, 6, 1)).one().price == 20000.0, [w for w in r["peringatan"] if "2026-06" in w][:1])
n0 = db.query(HargaBerasJenis).count()
r2 = pu.perbarui(db, sekarang=date(2026, 8, 5))
cek("idempoten: panggil ulang tidak menambah baris", db.query(HargaBerasJenis).count() == n0 and r2["ditambah"] == [], r2["ditambah"])
r3 = pu.perbarui(db, sekarang=date(2026, 8, 20))
cek("bulan berjalan (Agustus) tidak dimasukkan pada 20 Agustus", r3["ditambah"] == [])

def palsu_gagal_medium(kode, tgl):
    return None if (kode == "1_4" and tgl.month == 9) else palsu_ok(kode, tgl)
pu.ambil_harian = palsu_gagal_medium
r4 = pu.perbarui(db, sekarang=date(2026, 10, 5))                  # Agustus ok, September gagal untuk Medium II
bulan_ada = {(j, d.strftime("%Y-%m")) for j, d in db.query(HargaBerasJenis.jenis, HargaBerasJenis.date).all()}
cek("Agustus masuk, September berhenti karena Medium II kosong", [x["bulan"] for x in r4["ditambah"]] == ["2026-08"] and r4["berhenti_karena"] and "Medium II" in r4["berhenti_karena"], r4["berhenti_karena"])
cek("tidak ada September parsial (bulan bolong dihindari)", not any(b == "2026-09" for _, b in bulan_ada))
def palsu_mati(kode, tgl): return None
pu.ambil_harian = palsu_mati
r5 = pu.perbarui(db, sekarang=date(2026, 10, 5))
cek("sumber mati total: tidak menulis apa pun, melapor", r5["ditambah"] == [] and r5["berhenti_karena"] is not None)
db.close()

# tabel kosong
db = SessionLocal(); db.query(HargaBerasJenis).delete(); db.commit()
try:
    pu.perbarui(db, sekarang=date(2026, 10, 5)); cek("tabel kosong ditolak jelas", False)
except ValueError as e:
    cek("tabel kosong ditolak jelas", "seed_beras" in str(e))
db.close(); seed_beras.seed()

# ---------------- latih ulang ----------------
pu.ambil_harian = palsu_ok
db = SessionLocal(); pu.perbarui(db, sekarang=date(2026, 8, 5)); db.close()
rp.load_rice_models()
db = SessionLocal()
t0 = time.time()
diganti = rt.sinkron_dari_db(db)
dur = time.time() - t0
cek("latih ulang bila DB lebih baru (%.1f dtk)" % dur, diganti and rp.get_config()["data_akhir"] == "2026-07-01", rp.get_config()["data_akhir"])
cek("tidak latih ulang bila DB tidak lebih baru", rt.sinkron_dari_db(db) is False)
hist = rt.baca_series_db(db)["Medium II"]
res = rp.predict_rice("Medium II", hist, 1)
cek("prediksi memakai titik awal baru (Juli 2026 -> Agustus 2026)", res[0].date.strftime("%Y-%m") == "2026-08" and abs(res[0].naive - hist.iloc[-1]) < 1e-9, round(res[0].hybrid, 1))
db.close()

# kesetaraan: latih ulang dari DB == train_final pada data yang sama (CSV sampai Mei 2026)
db = SessionLocal(); db.query(HargaBerasJenis).delete(); db.commit(); db.close(); seed_beras.seed()
rp.load_rice_models()
db = SessionLocal()
cfg_a, mod_a = rt.latih(rt.baca_series_db(db), rp.get_config()); db.close()
rp_cfg, rp_mod = rp._state["bundle"]
import numpy as np
selisih = 0.0
for j in rp.list_rice_types():
    h = rt.baca_series_db(SessionLocal())[j] if False else None
db = SessionLocal(); ser = rt.baca_series_db(db); db.close()
rp.set_rice_models(cfg_a, mod_a)
baru = {j: [(s.hybrid, s.prophet, s.arima) for s in rp.predict_rice(j, ser[j], 3)] for j in rp.list_rice_types()}
rp.load_rice_models()
lama = {j: [(s.hybrid, s.prophet, s.arima) for s in rp.predict_rice(j, ser[j], 3)] for j in rp.list_rice_types()}
selisih = max(abs(a - b) for j in baru for x, y in zip(baru[j], lama[j]) for a, b in zip(x, y))
cek("model latih-ulang-di-backend == berkas train_final (selisih maks Rp %.4f)" % selisih, selisih < 0.01)

# ---------------- token admin dan endpoint ----------------
def port_bebas():
    s = socket.socket(); s.bind(("127.0.0.1", 0)); p = s.getsockname()[1]; s.close(); return p
PORT = port_bebas(); BASE = f"http://127.0.0.1:{PORT}"
server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=PORT, log_level="error"))
threading.Thread(target=server.run, daemon=True).start()
for _ in range(120):
    try: requests.get(BASE + "/", timeout=1); break
    except Exception: time.sleep(0.5)
cek("tanpa ADMIN_TOKEN: nonaktif 503", requests.post(BASE + "/admin/perbarui").status_code == 503)
os.environ["ADMIN_TOKEN"] = "rahasia-uji"
cek("token salah 401", requests.post(BASE + "/admin/perbarui", headers={"X-Admin-Token": "salah"}).status_code == 401)
cek("tanpa token 401", requests.post(BASE + "/admin/perbarui").status_code == 401)
cek("status tanpa token 401", requests.get(BASE + "/admin/status").status_code == 401)
info = requests.get(BASE + "/beras/info").json()
cek("/beras/info memuat data terakhir dan tanggal latih", info["data_terakhir"] == "2026-05-01" and info["model_data_akhir"], info)
pu.ambil_harian = palsu_ok
r = requests.post(BASE + "/admin/perbarui", headers={"X-Admin-Token": "rahasia-uji"})
cek("token benar: 202 dimulai", r.status_code == 202, r.json())
for _ in range(120):
    st = requests.get(BASE + "/admin/status", headers={"X-Admin-Token": "rahasia-uji"}).json()
    if not st["berjalan"]: break
    time.sleep(1)
cek("proses latar selesai tanpa galat dan model diganti", st["galat"] is None and st["model_diganti"] is True, {k: st[k] for k in ("galat", "model_diganti")})
cek("hasil: bulan baru masuk (sampai bulan penuh terakhir)", len(st["hasil"]["ditambah"]) >= 1, st["hasil"]["ditambah"][:2])
info2 = requests.get(BASE + "/beras/info").json()
cek("/beras/info bergeser setelah pembaruan", info2["data_terakhir"] > info["data_terakhir"] and info2["model_data_akhir"] == info2["data_terakhir"], info2)
p = requests.get(BASE + "/beras/prediksi", params={"jenis": "Medium II", "horizon": 1}).json()
cek("/beras/prediksi memakai titik awal baru", p["origin_date"] == info2["data_terakhir"], p["origin_date"])
r = requests.post(BASE + "/admin/perbarui", headers={"X-Admin-Token": "rahasia-uji"})
time.sleep(0.3)
st = requests.get(BASE + "/admin/status", headers={"X-Admin-Token": "rahasia-uji"}).json()
cek("pemanggilan ulang aman (202 atau 409), tidak merusak", r.status_code in (202, 409))
for _ in range(60):
    if not requests.get(BASE + "/admin/status", headers={"X-Admin-Token": "rahasia-uji"}).json()["berjalan"]: break
    time.sleep(1)

# ---------------- B. nyata ke BI (opsional) ----------------
if os.environ.get("UJI_NYATA") == "1":
    pu.ambil_harian = asli
    db = SessionLocal(); db.query(HargaBerasJenis).delete(); db.commit(); db.close(); seed_beras.seed()
    db = SessionLocal()
    t0 = time.time()
    r = pu.perbarui(db, sekarang=date(2026, 7, 5))                # hanya Juni 2026 (satu bulan, ~180 permintaan)
    cek("NYATA: Juni 2026 ditarik dari BI dalam %.0f dtk" % (time.time() - t0), [x["bulan"] for x in r["ditambah"]] == ["2026-06"], r)
    nilai = {j: db.query(HargaBerasJenis).filter_by(jenis=j, date=date(2026, 6, 1)).one().price for j in pu.JENIS_KODE}
    print("   rata-rata Juni 2026:", {j: round(v, 1) for j, v in nilai.items()})
    cek("NYATA: nilai masuk akal (Rp 10.000 sampai 20.000/kg)", all(10000 < v < 20000 for v in nilai.values()))
    db.close()

print(f"\n{sum(hasil)}/{len(hasil)} lulus")
server.should_exit = True
time.sleep(1)
try: os.remove(DB)
except Exception: pass
sys.exit(0 if all(hasil) else 1)
