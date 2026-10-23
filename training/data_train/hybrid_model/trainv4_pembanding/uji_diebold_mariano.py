"""
Uji Diebold-Mariano (h=1, koreksi Harvey-Leybourne-Newbold) antarmodel pada 29 bulan uji.
Memakai predictions_test_dengan_ar_arima.csv (baris uji sama dengan trainv3).
Uji dua sisi. H0: akurasi prediksi sama. Loss: kuadrat dan absolut.
"""
import os, sys, itertools
import numpy as np, pandas as pd
from scipy import stats
sys.stdout.reconfigure(encoding="utf-8")
HERE = os.path.dirname(os.path.abspath(__file__))
d = pd.read_csv(os.path.join(HERE, "predictions_test_dengan_ar_arima.csv"))
y = d["aktual"].values
M = {
    "Naive": d["Naive (harga bulan ini)"].values,
    "ARIMA(1,1,0) 2018": d["ARIMA(1,1,0) | jendela 2018 (Jan 2018 dst)"].values,
    "ARIMA(1,1,0) 2021": d["ARIMA(1,1,0) | jendela 2021 (Des 2020 dst)"].values,
    "AR(1) 2021": d["AR(1) level | jendela 2021 (Des 2020 dst)"].values,
    "XGBoost-only": d["XGBoost-only (tuned)"].values,
    "Hybrid": d["Hybrid (tuned)"].values,
    "Prophet": d["Prophet-only (tuned)"].values,
}
n = len(y)


def dm(e1, e2, power):
    l1, l2 = np.abs(e1) ** power, np.abs(e2) ** power
    dd = l1 - l2
    dbar = dd.mean()
    var = dd.var(ddof=0) / n  # h=1: tanpa autokovarians
    if var <= 0:
        return np.nan, np.nan
    stat = dbar / np.sqrt(var)
    hln = np.sqrt((n + 1 - 2 + 0) / n)  # h=1
    stat *= hln
    p = 2 * (1 - stats.t.cdf(abs(stat), df=n - 1))
    return stat, p


pairs = [("Naive", k) for k in M if k != "Naive"] + [("ARIMA(1,1,0) 2021", "XGBoost-only"),
         ("ARIMA(1,1,0) 2021", "Prophet"), ("Hybrid", "Prophet"), ("XGBoost-only", "Prophet"), ("XGBoost-only", "Hybrid")]
rows = []
for a, b in pairs:
    ea, eb = y - M[a], y - M[b]
    for pw, nm in ((2, "kuadrat"), (1, "absolut")):
        s, p = dm(ea, eb, pw)
        rows.append({"A": a, "B": b, "loss": nm, "DM": round(s, 2) if s == s else None, "p": round(p, 3) if p == p else None,
                     "lebih_baik": a if (np.abs(ea) ** pw).mean() < (np.abs(eb) ** pw).mean() else b})
r = pd.DataFrame(rows)
r.to_csv(os.path.join(HERE, "uji_diebold_mariano.csv"), index=False)
print(r.to_string(index=False))
print("\nPasangan signifikan (p < 0,05):")
print(r[r["p"] < 0.05].to_string(index=False) if (r["p"] < 0.05).any() else "tidak ada")
