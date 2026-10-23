"""
Endpoint admin untuk pembaruan harga bulanan. Dipanggil oleh layanan cron pihak ketiga.

Dilindungi header X-Admin-Token yang dicocokkan dengan variabel lingkungan ADMIN_TOKEN. Bila ADMIN_TOKEN tidak
diatur, endpoint nonaktif (503), jadi tidak pernah terbuka tanpa sengaja.

POST /admin/perbarui berjalan di latar belakang (cron biasanya punya batas waktu pendek) dan idempoten.
GET  /admin/status   hasil proses terakhir.
"""
import hmac
import logging
import os
import threading
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Header, HTTPException

from app.core.database import SessionLocal
from app.services import pihps_updater, rice_trainer

log = logging.getLogger("admin")
router = APIRouter(prefix="/admin", tags=["admin"])

_kunci = threading.Lock()
_status = {"berjalan": False, "mulai": None, "selesai": None, "hasil": None, "galat": None, "model_diganti": None}


def _cek_token(x_admin_token: Optional[str]):
    harapan = os.environ.get("ADMIN_TOKEN")
    if not harapan:
        raise HTTPException(status_code=503, detail="Pembaruan dinonaktifkan: ADMIN_TOKEN belum diatur.")
    if not x_admin_token or not hmac.compare_digest(x_admin_token.encode(), harapan.encode()):
        raise HTTPException(status_code=401, detail="Token salah.")


def _kerja():
    db = SessionLocal()
    try:
        hasil = pihps_updater.perbarui(db)
        diganti = rice_trainer.sinkron_dari_db(db)
        _status.update(hasil=hasil, galat=None, model_diganti=diganti)
    except Exception as e:
        log.exception("Pembaruan gagal")
        _status.update(hasil=None, galat=f"{type(e).__name__}: {e}", model_diganti=None)
    finally:
        db.close()
        _status.update(berjalan=False, selesai=datetime.now(timezone.utc).isoformat(timespec="seconds"))
        _kunci.release()


@router.post("/perbarui", status_code=202)
def perbarui(x_admin_token: Optional[str] = Header(default=None)):
    _cek_token(x_admin_token)
    if not _kunci.acquire(blocking=False):
        raise HTTPException(status_code=409, detail="Pembaruan sedang berjalan.")
    _status.update(berjalan=True, mulai=datetime.now(timezone.utc).isoformat(timespec="seconds"), selesai=None,
                   hasil=None, galat=None, model_diganti=None)
    threading.Thread(target=_kerja, name="perbarui-harga", daemon=True).start()
    return {"status": "dimulai", "cek": "/admin/status"}


@router.get("/status")
def status(x_admin_token: Optional[str] = Header(default=None)):
    _cek_token(x_admin_token)
    return dict(_status)
