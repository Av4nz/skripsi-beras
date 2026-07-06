---
title: Skripsi Beras Backend
emoji: 🍚
colorFrom: green
colorTo: blue
sdk: docker
app_port: 7860
pinned: false
---

# skripsi-beras-backend

FastAPI backend for a hybrid rice-price prediction system (Prophet + XGBoost).

## Environment variables (set these as Secrets in the Space settings)

- `DATABASE_URL` — PostgreSQL connection string (Supabase).
- `CORS_ORIGINS` — comma-separated list of allowed frontend origins,
  e.g. `https://your-frontend.vercel.app`.

The API listens on port `7860` and exposes `GET /` as a health check.
