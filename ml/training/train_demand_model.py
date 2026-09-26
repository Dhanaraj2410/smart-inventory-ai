"""
Trains the demand-forecasting regressor (predicts next-day units sold from
the same feature set as the classifier, minus the target leakage columns).

Same data-source resolution as train_stockout_model.py (Django ORM, else
CSV fallback). Saves: ml/models/demand_forecasting_model.pkl,
ml/models/demand_scaler.pkl
"""
import json
import os
import sys
import types

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.linear_model import LinearRegression
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

HERE = os.path.dirname(os.path.abspath(__file__))
ML_DIR = os.path.dirname(HERE)
MODELS_DIR = os.path.join(ML_DIR, "models")
DATA_DIR = os.path.join(ML_DIR, "data")

sys.path.insert(0, os.path.dirname(ML_DIR))
from ml.preprocessing.features import (  # noqa: E402
    build_daily_sales_frame, add_calendar_features, add_rolling_and_lag_features,
    add_inventory_features, REGRESSION_TARGET,
)

try:
    import xgboost as xgb
    HAS_XGBOOST = True
except ImportError:
    HAS_XGBOOST = False

REGRESSION_FEATURES = [
    "day", "week", "month", "day_of_week", "is_weekend",
    "rolling_7_day_sales", "rolling_14_day_sales", "rolling_30_day_sales",
    "average_daily_sales", "sales_growth", "sales_volatility",
    "lag_1", "lag_7", "lag_14",
    "current_stock", "supplier_lead_time", "safety_stock",
]


def _fake_product(row):
    return types.SimpleNamespace(
        current_stock=int(row["current_stock"]), supplier_lead_time=int(row["supplier_lead_time"]),
        safety_stock=int(row["safety_stock"]), sku=row["sku"],
    )


def _build_regression_frame(sales_records, product):
    df = build_daily_sales_frame(sales_records, product)
    if len(df) < 20:
        return None
    df = add_calendar_features(df)
    df = add_rolling_and_lag_features(df)
    df = add_inventory_features(df, product.current_stock, product.supplier_lead_time, product.safety_stock)
    df = df.dropna(subset=REGRESSION_FEATURES + [REGRESSION_TARGET])
    return df


def _load_from_django():
    from apps.products.models import Product
    from apps.sales.models import SalesRecord

    frames = []
    for product in Product.objects.filter(is_active=True):
        qs = SalesRecord.objects.filter(product=product)
        df = _build_regression_frame(qs, product)
        if df is not None:
            frames.append(df)
    return pd.concat(frames, ignore_index=True) if frames else None


def _load_from_csv():
    products_path = os.path.join(DATA_DIR, "sample_products.csv")
    sales_path = os.path.join(DATA_DIR, "sample_sales.csv")
    if not (os.path.exists(products_path) and os.path.exists(sales_path)):
        raise FileNotFoundError(
            "No sample data found. Run `python ml/data/generate_sample_data.py` first."
        )
    products_df = pd.read_csv(products_path)
    sales_df = pd.read_csv(sales_path)
    sales_df["date"] = pd.to_datetime(sales_df["date"])

    frames = []
    for _, prow in products_df.iterrows():
        records = sales_df[sales_df["product_id"] == prow["sku"]][["date", "quantity_sold"]].to_dict("records")
        product = _fake_product(prow)
        df = _build_regression_frame(records, product)
        if df is not None:
            frames.append(df)
    return pd.concat(frames, ignore_index=True) if frames else None


def load_training_data():
    try:
        df = _load_from_django()
        if df is not None:
            return df, "django_db"
    except Exception:
        pass
    df = _load_from_csv()
    return df, "csv_fallback"


def train_demand_model(persist_metrics=True):
    os.makedirs(MODELS_DIR, exist_ok=True)
    df, source = load_training_data()
    if df is None or df.empty:
        raise ValueError("No training data available for the demand model.")

    X = df[REGRESSION_FEATURES].astype(float)
    y = df[REGRESSION_TARGET].astype(float)

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    scaler = StandardScaler()
    X_train_s = scaler.fit_transform(X_train)
    X_test_s = scaler.transform(X_test)

    candidates = {
        "LinearRegression": LinearRegression(),
        "RandomForestRegressor": RandomForestRegressor(
            n_estimators=300, max_depth=10, min_samples_leaf=3, random_state=42, n_jobs=-1,
        ),
        "GradientBoostingRegressor": GradientBoostingRegressor(
            n_estimators=200, max_depth=4, learning_rate=0.05, random_state=42,
        ),
    }
    if HAS_XGBOOST:
        candidates["XGBoostRegressor"] = xgb.XGBRegressor(
            n_estimators=300, max_depth=5, learning_rate=0.05, random_state=42,
        )

    results = {}
    for name, model in candidates.items():
        model.fit(X_train_s, y_train)
        preds = model.predict(X_test_s)
        preds = np.clip(preds, 0, None)
        mae = mean_absolute_error(y_test, preds)
        rmse = float(np.sqrt(mean_squared_error(y_test, preds)))
        mape_mask = y_test > 0
        mape = float(np.mean(np.abs((y_test[mape_mask] - preds[mape_mask]) / y_test[mape_mask])) * 100) \
            if mape_mask.any() else None
        metrics = {
            "mae": round(float(mae), 3), "mse": round(float(mean_squared_error(y_test, preds)), 3),
            "rmse": round(rmse, 3), "r2": round(float(r2_score(y_test, preds)), 4),
            "mape": round(mape, 2) if mape is not None else None,
        }
        results[name] = {"model": model, "metrics": metrics}

    best_name = min(results, key=lambda n: results[n]["metrics"]["rmse"])
    best_model = results[best_name]["model"]

    joblib.dump(best_model, os.path.join(MODELS_DIR, "demand_forecasting_model.pkl"))
    joblib.dump(scaler, os.path.join(MODELS_DIR, "demand_scaler.pkl"))
    joblib.dump(REGRESSION_FEATURES, os.path.join(MODELS_DIR, "demand_features.pkl"))

    summary = {
        "best_model": best_name, "data_source": source, "training_samples": int(len(df)),
        "all_results": {n: r["metrics"] for n, r in results.items()},
    }
    with open(os.path.join(MODELS_DIR, "demand_model_metrics.json"), "w") as f:
        json.dump(summary, f, indent=2, default=str)

    if persist_metrics:
        try:
            from apps.predictions.models import ModelPerformance
            ModelPerformance.objects.filter(model_type="REGRESSION").update(is_active=False)
            for name, r in results.items():
                ModelPerformance.objects.create(
                    model_type="REGRESSION", model_name=name, metrics_json=r["metrics"],
                    is_active=(name == best_name), training_samples=len(df),
                )
        except Exception:
            pass

    return summary


if __name__ == "__main__":
    summary = train_demand_model(persist_metrics=False)
    print(json.dumps(summary, indent=2, default=str))
