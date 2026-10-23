"""
Pembaruan harga bulanan beras dari PIHPS (endpoint publik Bank Indonesia), untuk enam jenis, DIY, pasar tradisional.

Metode SAMA dengan training/.../tarik_6jenis_harian.py: harga harian per hari kalender (nilai terakhir diulang pada
akhir pekan dan libur oleh PIHPS), lalu rata-rata bulanan. Dengan metode sama, bulan baru sebanding dengan data
penelitian (Januari 2021 sampai Mei 2026).

Aturan:
  - hanya bulan penuh (bulan berjalan tidak dimasukkan; ada jeda 2 hari setelah akhir bulan);
  - satu bulan dimasukkan hanya bila KEENAM jenis terisi minimal 50 persen hari; bila gagal, berhenti di bulan itu
    sehingga tidak ada bulan bolong;
  - idempoten: baris (jenis, tanggal) yang sudah ada tidak ditimpa;
  - tidak ada nilai yang diubah atau dipaksa. Lonjakan besar hanya dilaporkan sebagai peringatan.
"""
import calendar
import logging
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timedelta, timezone
from typing import Dict, List, Optional

import requests
from sqlalchemy import func

from app.models.db_models import HargaBerasJenis

log = logging.getLogger("pihps_updater")

JENIS_KODE = {"Bawah I": "1_1", "Bawah II": "1_2", "Medium I": "1_3", "Medium II": "1_4", "Super I": "1_5", "Super II": "1_6"}
MIN_TERISI = 0.5
JEDA_HARI = 2
AMBANG_PERINGATAN = 0.20
_HEADERS = {"User-Agent": "Mozilla/5.0", "Accept": "application/json, text/javascript, */*; q=0.01",
            "X-Requested-With": "XMLHttpRequest", "Referer": "https://www.bi.go.id/hargapangan/"}
_sesi = requests.Session()
_sesi.headers.update(_HEADERS)


def ambil_harian(kode: str, tgl: date) -> Optional[float]:
    """Harga satu jenis pada satu hari, atau None bila tidak tersedia."""
    url = (f"https://www.bi.go.id/hargapangan/WebSite/Home/GetGridData1?tanggal={tgl.strftime('%b %d, %Y')}"
           f"&commodity={kode}&priceType=1&isPasokan=1&jenis=1&periode=1&provId=15")
    for _ in range(3):
        try:
            r = _sesi.get(url, timeout=20)
            if r.status_code == 200:
                dd = r.json().get("data") or []
                if dd and dd[0].get("Nilai") not in (None, ""):
                    return float(dd[0]["Nilai"])
                return None
        except Exception:
            time.sleep(1)
    return None


def _bulan_berikut(d: date) -> date:
    return date(d.year + (d.month == 12), d.month % 12 + 1, 1)


def bulan_penuh_setelah(terakhir: date, sekarang: date) -> List[date]:
    """Awal-bulan setelah `terakhir` yang sudah penuh (akhir bulan + JEDA_HARI sudah lewat)."""
    hasil, m = [], _bulan_berikut(terakhir.replace(day=1))
    while sekarang >= _bulan_berikut(m) + timedelta(days=JEDA_HARI - 1):
        hasil.append(m)
        m = _bulan_berikut(m)
    return hasil


def rata_bulan(tahun: int, bulan: int) -> Dict[str, dict]:
    """Rata-rata bulanan per jenis dari harga harian: {jenis: {rata, terisi, hari}}."""
    hari = [date(tahun, bulan, h) for h in range(1, calendar.monthrange(tahun, bulan)[1] + 1)]
    tugas = [(j, k, d) for j, k in JENIS_KODE.items() for d in hari]
    with ThreadPoolExecutor(max_workers=6) as ex:
        nilai = list(ex.map(lambda t: ambil_harian(t[1], t[2]), tugas))
    out = {j: {"v": [], "hari": len(hari)} for j in JENIS_KODE}
    for (j, _, _), v in zip(tugas, nilai):
        if v is not None:
            out[j]["v"].append(v)
    return {j: {"rata": (sum(o["v"]) / len(o["v"])) if o["v"] else None, "terisi": len(o["v"]), "hari": o["hari"]}
            for j, o in out.items()}


def sekarang_wib() -> date:
    return datetime.now(timezone(timedelta(hours=7))).date()


def perbarui(db, sekarang: Optional[date] = None) -> dict:
    """Tarik dan simpan bulan penuh yang belum ada. Mengembalikan ringkasan (tidak melempar karena sumber gagal)."""
    sekarang = sekarang or sekarang_wib()
    terakhir_per_jenis = dict(db.query(HargaBerasJenis.jenis, func.max(HargaBerasJenis.date))
                              .group_by(HargaBerasJenis.jenis).all())
    if len(terakhir_per_jenis) < len(JENIS_KODE):
        raise ValueError("Tabel harga_beras_jenis belum terisi untuk keenam jenis. Jalankan seed_beras dulu.")
    terakhir = min(terakhir_per_jenis.values())
    hasil = {"bulan_terakhir_sebelum": str(terakhir), "ditambah": [], "peringatan": [], "berhenti_karena": None}
    for awal in bulan_penuh_setelah(terakhir, sekarang):
        label = awal.strftime("%Y-%m")
        stat = rata_bulan(awal.year, awal.month)
        kurang = [f"{j} ({s['terisi']}/{s['hari']} hari)" for j, s in stat.items() if s["terisi"] < MIN_TERISI * s["hari"]]
        if kurang:
            hasil["berhenti_karena"] = f"{label}: data belum cukup untuk {', '.join(kurang)}"
            break
        baru = 0
        for jenis, s in stat.items():
            ada = db.query(HargaBerasJenis).filter(HargaBerasJenis.jenis == jenis, HargaBerasJenis.date == awal).first()
            if ada:
                continue
            prev = (db.query(HargaBerasJenis).filter(HargaBerasJenis.jenis == jenis, HargaBerasJenis.date < awal)
                    .order_by(HargaBerasJenis.date.desc()).first())
            harga = round(s["rata"], 2)
            if prev and abs(harga / prev.price - 1) > AMBANG_PERINGATAN:
                hasil["peringatan"].append(f"{label} {jenis}: berubah {100 * (harga / prev.price - 1):+.1f}% dari bulan sebelumnya")
            db.add(HargaBerasJenis(jenis=jenis, date=awal, price=harga))
            baru += 1
        db.commit()
        hasil["ditambah"].append({"bulan": label, "baris": baru})
    terakhir_baru = db.query(func.max(HargaBerasJenis.date)).scalar()
    hasil["bulan_terakhir_sesudah"] = str(terakhir_baru)
    return hasil
