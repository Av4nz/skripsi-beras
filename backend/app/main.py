import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.core.database import engine, Base
from app.services.model_loader import load_models
from app.api.routes import router as api_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Setup database tables
    Base.metadata.create_all(bind=engine)
    # Load ML models
    load_models()
    yield
    # Cleanup if needed

app = FastAPI(
    title="Hybrid Prediction API",
    description="FastAPI backend for a hybrid machine learning prediction system (Prophet + XGBoost).",
    version="1.0.0",
    lifespan=lifespan
)

# Configure CORS Middleware
# Set CORS_ORIGINS as a comma-separated list of allowed frontend URLs, e.g.
#   CORS_ORIGINS=http://localhost:3000,https://your-frontend.vercel.app
# Defaults to localhost:3000 for local development.
_cors_origins = os.getenv("CORS_ORIGINS", "http://localhost:3000")
allowed_origins = [origin.strip() for origin in _cors_origins.split(",") if origin.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],  # Allows all HTTP methods (GET, POST, etc.)
    allow_headers=["*"],  # Allows all headers
)

@app.get("/")
def health_check():
    return {"status": "ok", "service": "Hybrid Prediction API"}

app.include_router(api_router)
