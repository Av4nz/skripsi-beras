# Hasil Training Ulang: Skema Realistis (trainv3)

## Perubahan skema

| | Skema lama (trainv2, "skenario") | Skema baru (trainv3, realistis) |
|---|---|---|
| Target | harga bulan T | harga bulan **T+1** |
| Faktor eksternal | nilai bulan T (bulan yang diprediksi) | nilai bulan **T** (sudah diketahui saat prediksi) |
| Lag harga | harga T-1, T-2 | harga T, T-1, T-2, rata-rata 3 bulan, selisih T vs T-1 |
| Kalender | bulan & lebaran bulan T | bulan & lebaran bulan T+1 (jadwal sudah pasti) |

Faktor eksternal: `harga_gkg`, `curah_hujan`, `produksi_padi`, `inflasi_pangan`, ditambah selisih GKG bulan T vs T-1.

## Protokol

- Data: `trainv2/harga_beras_2018_2026.csv`. Target dari Jan 2021 s.d. Mei 2026 (65 baris).
- **Walk-forward, expanding window, refit tiap bulan.** Untuk bulan target M, model hanya dilatih dengan baris yang targetnya sebelum M.
- **Validasi (tuning hyperparameter):** target Jan 2023 s.d. Des 2023 (12 bulan), kriteria MAPE.
- **Uji (angka laporan):** target Jan 2024 s.d. Mei 2026 (29 bulan), tidak dipakai saat tuning.
- Baseline naive (harga bulan depan = harga bulan ini) disertakan sebagai pembanding minimum.
- "Arah" = persentase bulan saat arah perubahan (naik/turun/tetap) yang diprediksi sama dengan aktual.

## Ruang hyperparameter

| Model | Metode | Jumlah konfigurasi | Parameter |
|---|---|---|---|
| Prophet-only | Grid search | 192 | changepoint_prior_scale {0.01, 0.05, 0.1, 0.5}, seasonality_prior_scale {0.1, 1, 10}, seasonality_mode {additive, multiplicative}, fourier order yearly {3, 5}, regressor eksternal {tanpa, dengan prior_scale 0.5 / 2 / 10} |
| XGBoost-only | Random search | 81 (80 acak + default) | n_estimators, learning_rate, max_depth, subsample, colsample_bytree, min_child_weight, reg_alpha, reg_lambda, pakai faktor eksternal {ya, tidak}, target {level harga, selisih harga} |
| Hybrid | Top-3 Prophet x random search XGBoost | 183 (3 x 61) | Prophet: 3 konfigurasi terbaik di atas. XGBoost residual: ruang yang sama, pakai faktor eksternal {ya, tidak} |

## Hyperparameter terbaik

**Prophet-only (tuned):** changepoint_prior_scale=0.1, seasonality_prior_scale=0.1, mode=multiplicative, yearly fourier order=3, **tanpa faktor eksternal** (+ regressor lebaran).

**XGBoost-only (tuned):** n_estimators=50, learning_rate=0.05, max_depth=6, subsample=0.8, colsample_bytree=0.6, min_child_weight=1, reg_alpha=0, reg_lambda=5, target=selisih harga, **tanpa faktor eksternal**.

**Hybrid (tuned):** Prophet sama dengan Prophet-only tuned. XGBoost residual: n_estimators=50, learning_rate=0.01, max_depth=2, subsample=0.6, colsample_bytree=1.0, min_child_weight=1, reg_alpha=0, reg_lambda=5, **tanpa faktor eksternal**.

**Default** = parameter bawaan library (Prophet cps=0.05, sps=10, additive, fourier 10, + faktor eksternal. XGBoost n_estimators=100, lr=0.3, max_depth=6, + faktor eksternal, target level harga).

## Pengaruh faktor eksternal (validasi 2023, MAPE terbaik)

| Model | Tanpa faktor eksternal | Dengan faktor eksternal bulan T |
|---|---|---|
| Prophet-only | **1.30%** | 1.51% |
| XGBoost-only (target selisih) | **0.83%** | 0.96% |
| XGBoost-only (target level) | 1.18% | 1.19% |
| Hybrid | 1.304% | 1.305% |

Faktor eksternal bulan sebelumnya tidak membantu, bahkan sedikit memperburuk.

## Hasil utama (uji Jan 2024 s.d. Mei 2026, 29 bulan)

| Model | MAPE validasi 2023 | MAE uji (Rp) | RMSE uji (Rp) | MAPE uji | Arah |
|---|---|---|---|---|---|
| Naive (harga bulan ini) | 1.12% | 121.5 | 289.3 | **0.83%** | 52% |
| Prophet-only (default) | 21.03% | 276.5 | 371.4 | 1.94% | 10% |
| Prophet-only (tuned) | 1.30% | 383.0 | 468.9 | 2.69% | 24% |
| XGBoost-only (default) | 1.19% | 234.4 | 367.6 | 1.64% | 24% |
| **XGBoost-only (tuned)** | **0.83%** | **151.2** | 295.9 | **1.04%** | 28% |
| Hybrid (default) | 21.03% | 281.8 | 364.5 | 1.98% | 10% |
| Hybrid (tuned) | 1.30% | 367.5 | 454.6 | 2.58% | 24% |

## Per tahun (uji)

| Model | MAPE 2024 | MAPE 2025 | MAPE 2026 (Jan-Mei) |
|---|---|---|---|
| Naive | 1.58% | 0.44% | 0.00% |
| Prophet-only (default) | 2.83% | 1.62% | 0.57% |
| Prophet-only (tuned) | 2.82% | 2.51% | 2.80% |
| XGBoost-only (default) | 2.57% | 1.25% | 0.34% |
| XGBoost-only (tuned) | 1.89% | 0.58% | 0.11% |
| Hybrid (default) | 2.80% | 1.64% | 0.81% |
| Hybrid (tuned) | 2.73% | 2.42% | 2.59% |

## Prakiraan Juni 2026 (model final dilatih seluruh data)

| Model | Prediksi (Rp/kg) |
|---|---|
| Naive | 14,150 |
| Prophet-only (tuned) | 14,058 |
| XGBoost-only (tuned) | 14,170 |
| Hybrid (tuned) | 14,032 |

## Temuan penting

1. **Tidak ada model yang mengalahkan baseline naive** pada data uji (0.83%). Harga beras DIY bulanan sangat stabil (2026 harga tetap Rp14.150 selama 5 bulan), sehingga "harga bulan depan = harga bulan ini" sudah sangat kuat.
2. **XGBoost-only (tuned) adalah model terbaik** dari tiga arsitektur: MAPE 1.04%, menang di validasi dan uji. Kuncinya target berupa *selisih* harga (bukan level harga).
3. **Hybrid tidak lebih baik dari Prophet-only.** XGBoost residual hanya menggeser prediksi Prophet sedikit (2.69% ke 2.58%).
4. **Prophet tuned lebih buruk di uji daripada default** (2.69% vs 1.94%) walau jauh lebih baik di validasi (1.30% vs 21.03%). Prophet default dengan faktor eksternal sangat tidak stabil di data latih pendek (validasi 21%), lalu kebetulan cocok di periode uji. Ini tanda overfitting pada pemilihan hyperparameter dengan data sedikit.
5. **Faktor eksternal bulan T tidak menambah daya prediksi** untuk harga bulan T+1. Pada semua arsitektur, konfigurasi terbaik justru tanpa faktor eksternal. Angka trainv2 (MAPE ~2.9%) memakai protokol berbeda (prediksi blok setahun, faktor eksternal bulan target), jadi tidak bisa dibandingkan langsung dengan tabel di atas.

## Berkas

| Berkas | Isi |
|---|---|
| `train_realistic.py` | Skrip training, tuning, evaluasi |
| `results.json` | Semua metrik (validasi, uji, per tahun, arah), konfigurasi, prakiraan |
| `final_config.json` | Hyperparameter terbaik dan daftar fitur |
| `tuning_prophet.csv`, `tuning_xgboost.csv`, `tuning_hybrid.csv` | Hasil tiap konfigurasi tuning, urut MAPE validasi |
| `predictions_test.csv` | Prediksi per bulan uji untuk semua model |
| `final_*.pkl` | Model final dilatih pada seluruh data |
| `run.log` | Log run penuh (~71 menit) |

Jalankan ulang: `backend/.venv/Scripts/python.exe training/data_train/hybrid_model/trainv3_realistic/train_realistic.py`
(`SMOKE=1` untuk uji alur cepat tanpa menulis file.)
