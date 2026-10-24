"""
Uji Diebold-Mariano untuk KONFIGURASI FINAL (tanpa faktor eksternal, tanpa Lebaran), enam jenis, horizon 1 sampai 6.

Masukan: uji_horizon_<jenis>_tanpaLebaran_prediksi.csv (prediksi walk-forward per origin) dan data bulanan PIHPS.
Koreksi Harvey-Leybourne-Newbold untuk horizon h: varians selisih loss memakai autokovarians sampai lag h-1,
faktor koreksi sqrt((n + 1 - 2h + h(h-1)/n) / n), distribusi t dengan n-1 derajat bebas. Uji dua sisi.
Bila varians taksiran tidak positif (terjadi pada horizon panjang dengan sampel kecil), hasil dilaporkan kosong, bukan dipaksa.

Catatan: n kecil (24 sampai 29), galat antarmodel berkorelasi, dan keenam jenis bergerak serempak, jadi p-value bersifat indikatif.
"""
import os, sys
import numpy as np, pandas as pd
from scipy import stats
sys.stdout.reconfigure(encoding="utf-8")
HERE = os.path.dirname(os.path.abspath(__file__))
BUL = os.path.join(HERE, "..", "..", "datasets", "data_app", "datav2", "beras", "pihps_6jenis_diy_bulanan_2021-2026.csv")
b = pd.read_csv(BUL, index_col=0); b.index = pd.to_datetime(b.index + "-01")
LAST = pd.Timestamp("2026-05-01")
JENIS = ["Bawah I", "Bawah II", "Medium I", "Medium II", "Super I", "Super II"]
MODEL = {"Naive": "Naive", "ARIMA": "ARIMA(1,1,0)", "Prophet": "Prophet", "Hybrid": "Hybrid recursive"}
PASANGAN = [("Naive", "Hybrid"), ("Naive", "ARIMA"), ("ARIMA", "Hybrid"), ("Hybrid", "Prophet")]


def dm(e1, e2, power, h):
    n = len(e1)
    d = np.abs(e1) ** power - np.abs(e2) ** power
    dbar = d.mean()
    dc = d - dbar
    gam0 = (dc @ dc) / n
    s = gam0
    for k in range(1, h):
        s += 2 * (dc[k:] @ dc[:-k]) / n
    var = s / n
    if not np.isfinite(var) or var <= 0:
        return np.nan, np.nan
    stat = dbar / np.sqrt(var)
    kor = (n + 1 - 2 * h + h * (h - 1) / n) / n
    if kor <= 0:
        return np.nan, np.nan
    stat *= np.sqrt(kor)
    return float(stat), float(2 * (1 - stats.t.cdf(abs(stat), df=n - 1)))


rows = []
for j in JENIS:
    tag = j.replace(" ", "_") + ("_bulanan" if j == "Medium II" else "") + "_tanpaLebaran"
    P = pd.read_csv(os.path.join(HERE, f"uji_horizon_{tag}_prediksi.csv"), parse_dates=["origin"])
    for h in range(1, 7):
        tgt = P["origin"] + pd.DateOffset(months=h)
        ok = (tgt <= LAST).values
        y = b[j].reindex(tgt[ok].values).values
        n = int(ok.sum())
        pred = {k: P.loc[ok, f"{v}|{h}"].values for k, v in MODEL.items()}
        mape = {k: float(np.mean(np.abs(y - pred[k]) / y) * 100) for k in pred}
        for a, c in PASANGAN:
            ea, ec = y - pred[a], y - pred[c]
            for pw, nm in ((2, "kuadrat"), (1, "absolut")):
                st, p = dm(ea, ec, pw, h)
                la, lc = (np.abs(ea) ** pw).mean(), (np.abs(ec) ** pw).mean()
                rows.append({"jenis": j, "h": h, "n": n, "A": a, "B": c, "loss": nm,
                             "DM": round(st, 2) if st == st else None, "p": round(p, 4) if p == p else None,
                             "lebih_baik": a if la < lc else c, "MAPE_A": round(mape[a], 3), "MAPE_B": round(mape[c], 3)})
R = pd.DataFrame(rows)
R.to_csv(os.path.join(HERE, "uji_diebold_mariano_final.csv"), index=False)
print("baris:", len(R), "| n uji h=1:", int(R[R.h == 1].n.iloc[0]), "h=6:", int(R[R.h == 6].n.iloc[0]))

print("\n=== Medium II, horizon 1 sampai 6, loss absolut ===")
m = R[(R.jenis == "Medium II") & (R.loss == "absolut")]
print(m[["h", "n", "A", "B", "MAPE_A", "MAPE_B", "DM", "p", "lebih_baik"]].to_string(index=False))

print("\n=== Horizon 1, semua jenis, Naive lawan Hybrid, kedua loss ===")
x = R[(R.h == 1) & (R.A == "Naive") & (R.B == "Hybrid")]
print(x[["jenis", "loss", "MAPE_A", "MAPE_B", "DM", "p", "lebih_baik"]].to_string(index=False))

print("\n=== Horizon 1, semua jenis, Naive lawan ARIMA, kedua loss ===")
x = R[(R.h == 1) & (R.A == "Naive") & (R.B == "ARIMA")]
print(x[["jenis", "loss", "MAPE_A", "MAPE_B", "DM", "p", "lebih_baik"]].to_string(index=False))

print("\n=== Horizon 1, semua jenis, Hybrid lawan Prophet ===")
x = R[(R.h == 1) & (R.A == "Hybrid") & (R.B == "Prophet")]
print(x[["jenis", "loss", "MAPE_A", "MAPE_B", "DM", "p", "lebih_baik"]].to_string(index=False))

print("\n=== Ringkasan: Naive lawan Hybrid (loss absolut), jumlah (jenis x horizon) signifikan p<0,05 ===")
y = R[(R.A == "Naive") & (R.B == "Hybrid") & (R.loss == "absolut") & R.p.notna()]
print("diuji:", len(y), "| signifikan:", int((y.p < 0.05).sum()), "| naive lebih baik pada:", int((y.lebih_baik == "Naive").sum()))
print("tidak valid (varians tak positif):", int(R[(R.A == "Naive") & (R.B == "Hybrid") & (R.loss == "absolut")].p.isna().sum()))
