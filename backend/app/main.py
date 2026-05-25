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
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Replace ["*"] with your frontend URL(s) in production, e.g., ["http://localhost:3000"]
    allow_credentials=True,
    allow_methods=["*"],  # Allows all HTTP methods (GET, POST, etc.)
    allow_headers=["*"],  # Allows all headers
)

app.include_router(api_router)
