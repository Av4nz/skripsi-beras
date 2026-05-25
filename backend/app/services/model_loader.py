import json
import joblib
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.abspath(os.path.join(BASE_DIR, "../../"))

PROPHET_MODEL_PATH = os.path.join(ROOT_DIR, "ml_models", "prophet_model.pkl")
XGB_MODEL_PATH = os.path.join(ROOT_DIR, "ml_models", "best_xgb_model.pkl")
FEATURES_PATH = os.path.join(ROOT_DIR, "ml_models", "features.json")

prophet_model = None
xgb_model = None
features_config = None

def load_models():
    global prophet_model, xgb_model, features_config
    
    if os.path.exists(PROPHET_MODEL_PATH):
        prophet_model = joblib.load(PROPHET_MODEL_PATH)
    else:
        print(f"Warning: Prophet model not found at {PROPHET_MODEL_PATH}")
        
    if os.path.exists(XGB_MODEL_PATH):
        xgb_model = joblib.load(XGB_MODEL_PATH)
    else:
        print(f"Warning: XGBoost model not found at {XGB_MODEL_PATH}")
        
    if os.path.exists(FEATURES_PATH):
        with open(FEATURES_PATH, "r") as f:
            features_config = json.load(f)
    else:
        print(f"Warning: Features config not found at {FEATURES_PATH}")

def get_prophet_model():
    return prophet_model

def get_xgb_model():
    return xgb_model

def get_features_config():
    return features_config
