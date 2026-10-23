"""
============================================================================
 PEMBANDING TRADISIONAL AR / ARIMA -- protokol sama dengan trainv3
============================================================================
Permintaan pembimbing (23 Oktober 2026): tambahkan teknik pembanding
tradisional (AR atau ARIMA) di Bab IV.

Protokol identik dengan trainv3_realistic:
  - Prediksi 1 bulan ke depan: informasi sampai bulan T -> harga bulan T+1.
  - Walk-forward, expanding window, refit tiap bulan target.
  - Validasi (pemilihan orde): target 2023-01 .. 2023-12.
  - Uji (laporan): target 2024-01 .. 2026-05 (29 bulan), tidak dipakai tuning.
  - Bulan target dan harga aktual diambil dari trainv3/predictions_test.csv,
    sehingga baris uji dijamin sama dengan model lain.

Model:
  AR / ARIMA dengan grid orde (p, d, q), p dan q dalam 0..2, d dalam {0, 1}.
  d=0 memakai konstanta, d=1 tanpa konstanta. Orde dipilih dari MAPE validasi.
  Dua jendela latih: mulai Desember 2020 (sama dengan trainv3) dan mulai
  Januari 2018 (sensitivitas, memakai data sebelum 2021).

Tidak mengubah berkas trainv3. Keluaran di folder ini.

Jalankan (statsmodels ada di python sistem, belum ada di backend/.venv):
    python training/data_train/hybrid_model/trainv4_pembanding/train_ar_arima.py
============================================================================
"""
import os, sys, json, itertools, warnings
import numpy as np
import pandas as pd
from statsmodels.tsa.arima.model import ARIMA

warnings.filterwarnings("ignore")
sys.stdout.reconfigure(encoding="utf-8")

HERE = os.path.dirname(os.path.abspath(__file__))
V2 = os.path.join(HERE, "..", "trainv2", "harga_beras_2018_2026.csv")
V3 = os.path.join(HERE, "..", "trainv3_realistic", "predictions_test.csv")
VAL = ("2023-01-01", "2023-12-01")


def mape(y, p):
    y, p = np.asarray(y, float), np.asarray(p, float)
    return float(np.mean(np.abs(y - p) / y))


def metrics(y, p):
    y, p = np.asarray(y, float), np.asarray(p, float)
    return {"MAE": float(np.mean(np.abs(y - p))),
            "RMSE": float(np.sqrt(np.mean((y - p) ** 2))),
            "MAPE": mape(y, p)}


raw = pd.read_csv(V2)
raw["tanggal"] = pd.to_datetime(raw["tanggal"])
raw = raw.sort_values("tanggal").set_index("tanggal")
price = raw["harga_beras"].astype(float)
price.index = pd.DatetimeIndex(price.index, freq="MS")

test = pd.read_csv(V3)
test["bulan_target_T+1"] = pd.to_datetime(test["bulan_target_T+1"])
test["bulan_info_T"] = pd.to_datetime(test["bulan_info_T"])
test_targets = list(test["bulan_target_T+1"])
val_targets = list(pd.date_range(VAL[0], VAL[1], freq="MS"))


def forecast_one(order, origin, start):
    """Fit pada harga start..origin, ramal 1 langkah. Jatuh ke naive bila gagal."""
    y = price.loc[start:origin]
    p, d, q = order
    try:
        m = ARIMA(y, order=order, trend="c" if d == 0 else "n").fit()
        f = float(m.forecast(1).iloc[0])
        if not np.isfinite(f):
            raise ValueError
        return f, False
    except Exception:
        return float(y.iloc[-1]), True


def walk(order, targets, start):
    preds, fails = [], 0
    for t in targets:
        origin = t - pd.DateOffset(months=1)
        f, bad = forecast_one(order, origin, start)
        preds.append(f)
        fails += bad
    return np.array(preds), fails


def actual(targets):
    return price.loc[targets].values


grid = [o for o in itertools.product([0, 1, 2], [0, 1], [0, 1, 2]) if o != (0, 0, 0)]
results, tuning_rows = {}, []
for label, start in (("jendela 2021 (Des 2020 dst)", "2020-12-01"), ("jendela 2018 (Jan 2018 dst)", "2018-01-01")):
    rows = []
    for o in grid:
        pv, nf = walk(o, val_targets, start)
        rows.append({"jendela": label, "order": str(o), "p": o[0], "d": o[1], "q": o[2],
                     "val_MAPE": mape(actual(val_targets), pv), "gagal_fit": nf})
    tune = pd.DataFrame(rows).sort_values("val_MAPE").reset_index(drop=True)
    tuning_rows.append(tune)
    best = tuple(int(x) for x in (tune.loc[0, "p"], tune.loc[0, "d"], tune.loc[0, "q"]))
    # model sederhana yang selalu dilaporkan
    for name, o in (("AR(1) level", (1, 0, 0)), ("ARIMA(1,1,0)", (1, 1, 0)), (f"ARIMA{best} terbaik validasi", best)):
        pt, nf = walk(o, test_targets, start)
        pv, _ = walk(o, val_targets, start)
        y_t = actual(test_targets)
        origin_p = price.loc[[t - pd.DateOffset(months=1) for t in test_targets]].values
        key = f"{name} | {label}"
        results[key] = {"order": o, "gagal_fit_uji": nf,
                        "validation_2023": metrics(actual(val_targets), pv),
                        "test": metrics(y_t, pt),
                        "direction_acc_test": float(np.mean(np.sign(y_t - origin_p) == np.sign(pt - origin_p)))}
        test[key] = np.round(pt, 2)

pd.concat(tuning_rows).to_csv(os.path.join(HERE, "tuning_ar_arima.csv"), index=False)
test.to_csv(os.path.join(HERE, "predictions_test_dengan_ar_arima.csv"), index=False)

# gabungkan dengan hasil trainv3 dari berkas yang sama (bukan angka ketikan)
cols_v3 = ["Naive (harga bulan ini)", "XGBoost-only (tuned)", "Hybrid (tuned)", "Prophet-only (tuned)"]
y = test["aktual"].values
org = price.loc[list(test["bulan_info_T"])].values
semua = {}
for c in cols_v3:
    semua[c] = {"test": metrics(y, test[c].values),
                "direction_acc_test": float(np.mean(np.sign(y - org) == np.sign(test[c].values - org)))}
for k, v in results.items():
    semua[k] = {"test": v["test"], "direction_acc_test": v["direction_acc_test"],
                "validation_2023": v["validation_2023"], "order": v["order"], "gagal_fit_uji": v["gagal_fit_uji"]}
with open(os.path.join(HERE, "results.json"), "w", encoding="utf-8") as f:
    json.dump(semua, f, indent=2, ensure_ascii=False, default=str)

print(f"{'Model':<62}{'val MAPE':>9}{'MAPE uji':>10}{'MAE':>8}{'RMSE':>8}{'Arah':>6}")
for k, v in sorted(semua.items(), key=lambda kv: kv[1]["test"]["MAPE"]):
    vm = f"{v['validation_2023']['MAPE']:.2%}" if "validation_2023" in v else "-"
    print(f"{k:<62}{vm:>9}{v['test']['MAPE']:>10.2%}{v['test']['MAE']:>8.1f}{v['test']['RMSE']:>8.1f}{v['direction_acc_test']:>6.0%}")
print("\nTuning (5 terbaik per jendela):")
for t in tuning_rows:
    print(t.head(5)[["jendela", "order", "val_MAPE", "gagal_fit"]].to_string(index=False))
