**Tabel Perbandingan Kinerja Model** (data latih 2021-04-01–2024-12-01, data uji 2025-01-01–2025-12-01, prakiraan 1 bulan ke depan)

| Model | MAE (Rp) | RMSE (Rp) | MAPE |
|---|---|---|---|
| Prophet-only | 422.0 | 611.7 | 2.99% |
| XGBoost-only | 111.4 | 154.0 | 0.78% |
| Hybrid (Prophet+XGBoost) | 422.0 | 611.7 | 2.99% |

**Kinerja pada prakiraan banyak bulan ke depan (recursive)**

| Model | MAE (Rp) | RMSE (Rp) | MAPE |
|---|---|---|---|
| Prophet-only (tanpa lag, sama sprt one-step) | 422.0 | 611.7 | 2.99% |
| XGBoost-only | 114.6 | 163.6 | 0.81% |
| Hybrid (Prophet+XGBoost) | 422.0 | 611.7 | 2.99% |
