import requests
import pandas as pd
import time
from datetime import datetime

# 1. Konfigurasi Parameter Dasar
COMMODITY_ID = "1_4"  # Contoh: Beras Kualitas Medium II
PROV_ID = "15"        # Contoh: DIY
START_DATE = "2025-12-01"
END_DATE = "2026-05-31"  # Hari ini

# 2. Header (Penting agar tidak dianggap bot)
headers = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36",
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "X-Requested-With": "XMLHttpRequest",
    "Referer": "https://www.bi.go.id/hargapangan/"
}

# 3. Generate Range Tanggal (semua hari, termasuk akhir pekan)
date_list = pd.date_range(start=START_DATE, end=END_DATE)
all_data = []

# Untuk melacak TanggalAPI yang sudah pernah muncul agar tidak duplikat
seen_api_dates = set()

print(f"Memulai scraping data dari {START_DATE} sampai {END_DATE}...")

# 4. Looping Request
for current_date in date_list:
    # Tanggal dari loop (bukan dari API)
    tanggal_loop = current_date.strftime("%Y-%m-%d")

    # Format tanggal sesuai kebutuhan API
    str_date = current_date.strftime("%b %d, %Y")

    url = (
        f"https://www.bi.go.id/hargapangan/WebSite/Home/GetGridData1"
        f"?tanggal={str_date}&commodity={COMMODITY_ID}&priceType=1"
        f"&isPasokan=1&jenis=1&periode=1&provId={PROV_ID}"
    )

    row = {"Tanggal_Loop": tanggal_loop}  # Selalu isi Tanggal_Loop dari loop

    try:
        response = requests.get(url, headers=headers, timeout=10)

        if response.status_code == 200:
            json_res = response.json()
            if "data" in json_res and len(json_res["data"]) > 0:
                data_point = json_res["data"][0]
                api_tanggal = data_point.get("Tanggal", "")

                if api_tanggal not in seen_api_dates:
                    # Data baru dari API — ambil semua kolom
                    seen_api_dates.add(api_tanggal)
                    row.update({
                        "Provinsi": data_point.get("Provinsi", ""),
                        "Tanggal": api_tanggal,
                        "Komoditas": data_point.get("Komoditas", ""),
                        "Harga_Rp": data_point.get("Nilai", ""),
                        "Perubahan_Harga": data_point.get("NilaiDiff", ""),
                    })
                    print(f"Success : {tanggal_loop} | API={api_tanggal} | Harga: {data_point.get('Nilai')}")
                else:
                    # TanggalAPI sudah pernah muncul (duplikat akhir pekan/libur)
                    # Tetap catat baris ini dengan Tanggal_Loop, tapi kosongkan data API
                    row.update({
                        "Provinsi": "", "Tanggal": "", "Komoditas": "",
                        "Harga_Rp": "", "Perubahan_Harga": "",
                    })
                    print(f"Duplikat: {tanggal_loop} | API={api_tanggal} sudah dipakai, kolom API dikosongkan")
            else:
                # API tidak mengembalikan data untuk tanggal ini
                row.update({
                    "Provinsi": "", "Tanggal": "", "Komoditas": "",
                    "Harga_Rp": "", "Perubahan_Harga": "",
                })
                print(f"Empty   : {tanggal_loop} (Data tidak tersedia)")
        else:
            row.update({
                "Provinsi": "", "Tanggal": "", "Komoditas": "",
                "Harga_Rp": "", "Perubahan_Harga": "",
            })
            print(f"Failed  : {tanggal_loop} | Status: {response.status_code}")

    except Exception as e:
        row.update({
            "Provinsi": "", "Tanggal": "", "Komoditas": "",
            "Harga_Rp": "", "Perubahan_Harga": "",
        })
        print(f"Error   : {tanggal_loop} | {e}")

    all_data.append(row)  # Selalu append, tidak ada yang di-skip

    # Jeda agar tidak membebani server (Ethical Scraping)
    time.sleep(0.5)

# 5. Simpan Hasil Akhir
df = pd.DataFrame(all_data, columns=[
    "Tanggal_Loop", "Tanggal", "Provinsi", "Komoditas", "Harga_Rp", "Perubahan_Harga"
])

filename = "beras_2025-2026.csv"
df.to_csv(filename, index=False)

print(f"\nSelesai! {len(df)} baris data disimpan ke {filename}")
print(df.head(10))