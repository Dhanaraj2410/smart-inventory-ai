"""
Loads the trained model artifacts (joblib .pkl files under ml/models/) and
serves predictions. Models are loaded once per process and cached in module
globals -- NOT reloaded on every request (see project spec section 35,
"avoid loading ML models repeatedly").

If no trained model exists yet (fresh clone, before `python manage.py
train_models` has been run), every function here returns None so callers
fall back to their rule-based estimate (see apps.predictions.services and
apps.forecasting.services) instead of raising.
"""
import os

import joblib
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ML_DIR = os.path.dirname(HERE)
MODELS_DIR = os.path.join(ML_DIR, "models")

_stockout_cache = {}
_demand_cache = {}


def _load(cache, filename):
    if filename in cache:
        return cache[filename]
    path = os.path.join(MODELS_DIR, filename)
    if not os.path.exists(path):
        cache[filename] = None
        return None
    obj = joblib.load(path)
    cache[filename] = obj
    return obj


def _sales_queryset_for(product):
    from apps.sales.models import SalesRecord
    return SalesRecord.objects.filter(product=product)


def predict_stockout_risk(product, horizon_days=7):
    model = _load(_stockout_cache, "stockout_model.pkl")
    scaler = _load(_stockout_cache, "stockout_scaler.pkl")
    feature_cols = _load(_stockout_cache, "stockout_features.pkl")
    if model is None or scaler is None:
        return None

    from ml.preprocessing.features import build_prediction_row
    row = build_prediction_row(_sales_queryset_for(product), product)
    if row is None or row.empty:
        return None

    X = row[feature_cols].astype(float)
    X_s = scaler.transform(X)
    proba = float(model.predict_proba(X_s)[0, 1]) if hasattr(model, "predict_proba") else float(model.predict(X_s)[0])

    if proba >= 0.66:
        risk_level = "HIGH"
    elif proba >= 0.33:
        risk_level = "MEDIUM"
    else:
        risk_level = "LOW"

    factors = _explain_factors(model, feature_cols, X.iloc[0], product)
    return {"risk_level": risk_level, "probability": round(proba, 4), "factors": factors}


def _explain_factors(model, feature_cols, row, product):
    """Feature-importance-based explanation: ranks the features the trained
    model relies on most, then reports the ones where this product's actual
    value looks risk-elevating. This is a real (if simple) use of the
    model's own feature_importances_ / coef_ -- not an invented narrative."""
    importances = None
    if hasattr(model, "feature_importances_"):
        importances = model.feature_importances_
    elif hasattr(model, "coef_"):
        importances = np.abs(model.coef_[0])
    if importances is None:
        return []

    ranked = sorted(zip(feature_cols, importances), key=lambda t: -t[1])[:6]
    factors = []
    for name, _ in ranked:
        value = row.get(name)
        if name == "stock_to_demand_ratio" and value is not None and value < product.supplier_lead_time:
            factors.append(f"Current stock covers only ~{value:.1f} days of average demand")
        elif name == "sales_growth" and value is not None and value > 0.1:
            factors.append(f"Recent sales growth of {value:.0%}")
        elif name == "supplier_lead_time":
            factors.append(f"Supplier lead time is {product.supplier_lead_time} days")
        elif name in ("rolling_7_day_sales", "average_daily_sales") and value is not None:
            factors.append(f"{name.replace('_', ' ')} is {value:.1f}")
        if len(factors) >= 4:
            break
    return factors


def predict_demand(product, horizon_days=7):
    """Iterative multi-step forecast: predicts day+1, appends it as the new
    lag_1 to build day+2's features, and so on. This is the standard
    approach for turning a single-step regressor into a multi-day forecast
    without training a separate model per horizon."""
    model = _load(_demand_cache, "demand_forecasting_model.pkl")
    scaler = _load(_demand_cache, "demand_scaler.pkl")
    feature_cols = _load(_demand_cache, "demand_features.pkl")
    if model is None or scaler is None:
        return None

    from ml.preprocessing.features import build_daily_sales_frame, add_calendar_features, add_rolling_and_lag_features, add_inventory_features
    import pandas as pd

    df = build_daily_sales_frame(_sales_queryset_for(product), product)
    if df.empty or len(df) < 15:
        return None

    predictions = []
    working = df.copy()
    for step in range(horizon_days):
        working = add_calendar_features(working)
        working = add_rolling_and_lag_features(working)
        working = add_inventory_features(working, product.current_stock, product.supplier_lead_time,
                                          product.safety_stock)
        last_row = working.iloc[[-1]][feature_cols].astype(float)
        X_s = scaler.transform(last_row)
        pred = max(0.0, float(model.predict(X_s)[0]))
        predictions.append(round(pred, 2))

        next_date = working["date"].iloc[-1] + pd.Timedelta(days=1)
        new_row = pd.DataFrame([{"date": next_date, "quantity_sold": pred}])
        working = pd.concat([working[["date", "quantity_sold"]], new_row], ignore_index=True)

    return predictions
