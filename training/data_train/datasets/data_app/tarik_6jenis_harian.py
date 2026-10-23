"""
Tarik harga harian 6 jenis beras PIHPS (DIY, pasar tradisional) lalu hitung rata-rata bulanan.
Periode: 2021-01-01 .. 2026-05-31. Hanya membaca endpoint publik. Dapat dilanjutkan bila terhenti
(hasil per jenis disimpan ke berkas sementara).

Keluaran:
  datav2/beras/pihps_6jenis_diy_harian_2021-2026.csv   (tanggal, jenis, harga)
  datav2/beras/pihps_6jenis_diy_bulanan_2021-2026.csv  (rata-rata bulanan per jenis, kolom: bulan, 6 jenis)

Catatan metode: PIHPS mengulang nilai terakhir pada akhir pekan dan libur. Mengikuti dataset Medium II
yang sudah ada, baris duplikat tanggal API tetap dihitung apa adanya dalam rata-rata harian (hari kalender).
"""
import os, sys, time
import requests
import pandas as pd
from concurrent.futures import ThreadPoolExecutor

sys.stdout.reconfigure(encoding="utf-8")
BASE = r"D:\NGODING\skripsi-prediksi-beras\skripsi-beras\training\data_train\datasets\data_app\datav2\beras"
H = {"User-Agent": "Mozilla/5.0", "Accept": "application/json, text/javascript, */*; q=0.01",
     "X-Requested-With": "XMLHttpRequest", "Referer": "https://www.bi.go.id/hargapangan/"}
NAMA = {"1_1": "Bawah I", "1_2": "Bawah II", "1_3": "Medium I", "1_4": "Medium II", "1_5": "Super I", "1_6": "Super II"}
DAYS = pd.date_range("2021-01-01", "2026-05-31")
sess = requests.Session(); sess.headers.update(H)


def ambil(args):
    cid, d = args
    s = d.strftime("%b %d, %Y")
    url = (f"https://www.bi.go.id/hargapangan/WebSite/Home/GetGridData1?tanggal={s}&commodity={cid}"
           f"&priceType=1&isPasokan=1&jenis=1&periode=1&provId=15")
    for _ in range(3):
        try:
            r = sess.get(url, timeout=20)
            if r.status_code == 200:
                dd = r.json().get("data") or []
                if dd and dd[0].get("Nilai") not in (None, ""):
                    return d, float(dd[0]["Nilai"])
                return d, None
        except Exception:
            time.sleep(1)
    return d, None


for cid, nm in NAMA.items():
    tmp = os.path.join(BASE, f"_tmp_{cid}.csv")
    if os.path.exists(tmp):
        print(nm, "sudah ada, dilewati", flush=True)
        continue
    t0 = time.time()
    with ThreadPoolExecutor(max_workers=6) as ex:
        res = list(ex.map(ambil, [(cid, d) for d in DAYS]))
    df = pd.DataFrame(res, columns=["tanggal", "harga"]); df["jenis"] = nm
    df.to_csv(tmp, index=False)
    print(f"{nm}: {df['harga'].notna().sum()} dari {len(df)} hari terisi ({time.time()-t0:.0f} dtk)", flush=True)

harian = pd.concat([pd.read_csv(os.path.join(BASE, f"_tmp_{c}.csv"), parse_dates=["tanggal"]) for c in NAMA], ignore_index=True)
harian.to_csv(os.path.join(BASE, "pihps_6jenis_diy_harian_2021-2026.csv"), index=False)
harian["bulan"] = harian["tanggal"].dt.strftime("%Y-%m")
bul = harian.groupby(["bulan", "jenis"])["harga"].mean().unstack()[list(NAMA.values())]
bul.round(2).to_csv(os.path.join(BASE, "pihps_6jenis_diy_bulanan_2021-2026.csv"))
print("bulan:", len(bul), "| kosong per jenis:"); print(bul.isna().sum().to_string())
