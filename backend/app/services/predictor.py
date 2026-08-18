import pandas as pd
import numpy as np
import datetime
from sqlalchemy.orm import Session
from app.models.db_models import HargaBeras
from app.schemas.schemas import PredictionRequest, TimeSeriesPoint, ExternalFeatures
from app.services.model_loader import get_prophet_model, get_xgb_model, get_features_config

# Human-readable labels for the prediction decomposition components.
REGRESSOR_LABELS = {
    "harga_gkg": "Harga Gabah Kering Giling",
    "curah_hujan": "Curah Hujan",
    "produksi_padi": "Produksi Padi",
    "inflasi_pangan": "Inflasi Pangan",
    "lebaran": "Lebaran (Idulfitri)",
}
SEASONALITY_LABELS = {
    "yearly": "Pola Musiman Tahunan",
    "weekly": "Pola Musiman Mingguan",
    "daily": "Pola Musiman Harian",
}


def compute_decomposition(prophet, prophet_pred):
    """
    Descriptive breakdown of a single Prophet base prediction into
    trend + seasonal + external-regressor contributions (in Rupiah).

    For multiplicative components, the Rupiah contribution is approximated as
    trend * component_factor, so that trend + sum(contributions) ~= yhat.
    This describes the Prophet base prediction only; the final hybrid value
    additionally includes a small XGBoost residual correction and output bounds.
    Returns None if components cannot be extracted (kept optional/safe).
    """
    try:
        row = prophet_pred.iloc[0]
        trend = float(row["trend"])
        components = []

        def add_component(name, label, mode):
            if name not in prophet_pred.columns:
                return
            value = float(row[name])
            contribution = trend * value if mode == "multiplicative" else value
            components.append({"name": name, "label": label, "contribution": contribution})

        # Seasonal components (e.g., yearly)
        for name, cfg in getattr(prophet, "seasonalities", {}).items():
            add_component(name, SEASONALITY_LABELS.get(name, name), cfg.get("mode"))

        # External-regressor components (the 5 supporting variables)
        for name, cfg in getattr(prophet, "extra_regressors", {}).items():
            add_component(name, REGRESSOR_LABELS.get(name, name), cfg.get("mode"))

        return {"trend": trend, "components": components}
    except Exception:
        return None


def get_last_n_prices(db: Session, n: int = 3):
    records = db.query(HargaBeras).order_by(HargaBeras.date.desc()).limit(n).all()
    return list(reversed(records))

def get_historical_residuals(dates, prices, lebaran_past, exog_past, prophet):
    """
    Compute the last 2 residuals (T-1, T0) dynamically from the Prophet model.

    NOTE: Prophet carries external regressors (harga_gkg, curah_hujan,
    produksi_padi, inflasi_pangan), so the ACTUAL historical exogenous values
    (from `exog_past`) are supplied to Prophet.predict to ensure every
    registered regressor is available.
    """
    past_dates_df = pd.DataFrame({
        "ds": dates[1:3],
        "lebaran": lebaran_past[1:3],
        "harga_gkg": [exog_past[1]["harga_gkg"], exog_past[2]["harga_gkg"]],
        "curah_hujan": [exog_past[1]["curah_hujan"], exog_past[2]["curah_hujan"]],
        "produksi_padi": [exog_past[1]["produksi_padi"], exog_past[2]["produksi_padi"]],
        "inflasi_pangan": [exog_past[1]["inflasi_pangan"], exog_past[2]["inflasi_pangan"]],
    })
    prophet_past_pred = prophet.predict(past_dates_df)

    yhat_T_minus_1 = prophet_past_pred.loc[0, "yhat"]
    yhat_T0 = prophet_past_pred.loc[1, "yhat"]

    R_T_minus_1 = prices[1] - yhat_T_minus_1
    R_T0 = prices[2] - yhat_T0

    return R_T_minus_1, R_T0

def predict_hybrid(db: Session, request: PredictionRequest):
    prophet = get_prophet_model()
    xgb = get_xgb_model()
    features_config = get_features_config()

    if not prophet or not xgb:
        raise ValueError("Models are not loaded properly.")

    # Get last 3 actual prices for lag and rolling calculations
    last_records = get_last_n_prices(db, 3)
    if len(last_records) < 3:
        raise ValueError("Not enough historical data in DB to calculate lags. Need at least 3 records.")

    # We have T-2, T-1, T0
    P = [r.price for r in last_records]
    dates = [r.date for r in last_records]
    lebaran_past = [r.lebaran for r in last_records]
    # Historical exogenous values (needed because Prophet now has exog regressors).
    exog_past = [
        {"harga_gkg": r.harga_gkg, "curah_hujan": r.curah_hujan,
         "produksi_padi": r.produksi_padi, "inflasi_pangan": r.inflasi_pangan}
        for r in last_records
    ]

    # Resolve External Features (Fallback to last known if missing)
    if request.external_features is not None:
        ext_feat = request.external_features
    else:
        last_rec = last_records[-1]
        if last_rec.harga_gkg is None:
            raise ValueError("No external_features provided, and historical DB has no fallback features available.")
        ext_feat = ExternalFeatures(
            harga_gkg=last_rec.harga_gkg,
            curah_hujan=last_rec.curah_hujan,
            produksi_padi=last_rec.produksi_padi,
            inflasi_pangan=last_rec.inflasi_pangan,
            lebaran=last_rec.lebaran
        )

    # Get residuals (T-1, T0)
    R_T_minus_1, R_T0 = get_historical_residuals(dates, P, lebaran_past, exog_past, prophet)
    R = [0, R_T_minus_1, R_T0]

    predictions = []
    steps_details = []
    
    current_date = dates[-1]
    
    for i in range(request.period):
        # Determine next date (increment by 1 month)
        current_date = (pd.to_datetime(current_date) + pd.DateOffset(months=1)).date()
        
        # Calculate dynamic lags
        lag_1 = P[-1]
        lag_2 = P[-2]
        rolling_mean_3 = (P[-3] + P[-2] + P[-1]) / 3
        residual_lag_1 = R[-1]
        residual_lag_2 = R[-2]
        
        # Cyclical Month Encoding
        month = current_date.month
        month_sin = np.sin(2 * np.pi * month / 12)
        month_cos = np.cos(2 * np.pi * month / 12)
        
        features_dict = {
            "harga_gkg": ext_feat.harga_gkg,
            "curah_hujan": ext_feat.curah_hujan,
            "produksi_padi": ext_feat.produksi_padi,
            "inflasi_pangan": ext_feat.inflasi_pangan,
            "lag_1": lag_1,
            "lag_2": lag_2,
            "rolling_mean_3": rolling_mean_3,
            "residual_lag_1": residual_lag_1,
            "residual_lag_2": residual_lag_2,
            "month_sin": month_sin,
            "month_cos": month_cos
        }
        
        # 1. Base Prophet Prediction
        future_df = pd.DataFrame({
            "ds": [current_date],
            "lebaran": [ext_feat.lebaran],
            "harga_gkg": [ext_feat.harga_gkg],
            "curah_hujan": [ext_feat.curah_hujan],
            "produksi_padi": [ext_feat.produksi_padi],
            "inflasi_pangan": [ext_feat.inflasi_pangan],
        })
        prophet_pred = prophet.predict(future_df)
        yhat = float(prophet_pred.loc[0, "yhat"])

        # Descriptive decomposition of the Prophet base prediction
        # (trend + seasonal + external-regressor contributions).
        decomposition = compute_decomposition(prophet, prophet_pred)

        # 2. XGBoost Residual Correction
        # Feature Ordering Safety: Ensure exact order and check for missing features
        feature_cols = features_config["features"]
        ordered_features = {}
        for col in feature_cols:
            if col not in features_dict:
                raise ValueError(f"Missing required feature for XGBoost: '{col}'. Check features.json and predictor.py logic.")
            ordered_features[col] = features_dict[col]
            
        X_df = pd.DataFrame([ordered_features])
        predicted_residual = float(xgb.predict(X_df)[0])
        
        # 3. Final Prediction
        final_prediction = yhat + predicted_residual
        
        # --- Prediction Constraints ---
        # 1. Volatility constraint: Prevent runaway compounding in multi-step predictions.
        max_change_ratio = 0.10
        upper_bound = P[-1] * (1 + max_change_ratio)
        lower_bound = P[-1] * (1 - max_change_ratio)

        if final_prediction > upper_bound:
            final_prediction = upper_bound
        elif final_prediction < lower_bound:
            final_prediction = lower_bound
            
        # 2. Absolute Minimum price constraint: Beras price shouldn't fall below GKG price + margin.
        # We apply this AFTER the volatility constraint to ensure it takes absolute precedence.
        minimum_price = ext_feat.harga_gkg * 1.2
        if final_prediction < minimum_price:
            final_prediction = minimum_price
        # ------------------------------
        predictions.append(final_prediction)
        
        # Record step details
        steps_details.append({
            "step": i + 1,
            "date": current_date,
            "yhat": yhat,
            "residual": predicted_residual,
            "final_prediction": final_prediction,
            "features_used": features_dict,
            "decomposition": decomposition
        })
        
        # Update P and R for next iteration
        P.append(final_prediction)
        R.append(predicted_residual)

    # Fetch historical series for chart
    history = db.query(HargaBeras).order_by(HargaBeras.date.desc()).limit(60).all()
    history = list(reversed(history))
    
    series = []
    for h in history:
        series.append(TimeSeriesPoint(date=h.date, value=h.price, type="actual"))
        
    for step in steps_details:
        series.append(TimeSeriesPoint(date=step["date"], value=step["final_prediction"], type="forecast"))
        
    return {
        "prediction": predictions[0] if len(predictions) == 1 else predictions,
        "series": series,
        "details": {
            "steps": steps_details
        }
    }
