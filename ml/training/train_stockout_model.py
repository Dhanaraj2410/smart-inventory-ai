"""
Trains the stockout-risk classifier.

Data source resolution order:
  1. Django ORM (apps.sales.models.SalesRecord / apps.products.models.Product)
     -- used automatically when this is invoked from inside the Django app
     (management command `python manage.py train_models`, or a Celery task).
  2. CSV fallback (ml/data/sample_sales.csv + sample_products.csv) -- lets
     this module be trained/tested standalone (`python -m ml.training.train_stockout_model`)
     without a configured Django project/database, e.g. for a quick sanity
     check of the pipeline.

Saves: ml/models/stockout_model.pkl, ml/models/stockout_scaler.pkl
"""
import json
import os
import sys
import types

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score, roc_auc_score, confusion_matrix,
)

HERE = os.path.dirname(os.path.abspath(__file__))
ML_DIR = os.path.dirname(HERE)
MODELS_DIR = os.path.join(ML_DIR, "models")
DATA_DIR = os.path.join(ML_DIR, "data")

sys.path.insert(0, os.path.dirname(ML_DIR))  # project root, so `ml.preprocessing` imports cleanly
from ml.preprocessing.features import (  # noqa: E402
    build_training_frame, FEATURE_COLUMNS, CLASSIFICATION_TARGET,
)

try:
    import xgboost as xgb
    HAS_XGBOOST = True
except ImportError:
    HAS_XGBOOST = False

HORIZON_DAYS = 7


def _fake_product(row):
    return types.SimpleNamespace(
        current_stock=int(row["current_stock"]), supplier_lead_time=int(row["supplier_lead_time"]),
        safety_stock=int(row["safety_stock"]), sku=row["sku"],
    )


def _load_from_django():
    from apps.products.models import Product
    from apps.sales.models import SalesRecord

    frames = []
    for product in Product.objects.filter(is_active=True):
        qs = SalesRecord.objects.filter(product=product).values("date", "quantity_sold")
        df = build_training_frame(qs, product, horizon_days=HORIZON_DAYS)
        if df is not None and len(df) > 20:
            df["sku"] = product.sku
            frames.append(df)
    if not frames:
        return None
    return pd.concat(frames, ignore_index=True)


def _load_from_csv():
    products_path = os.path.join(DATA_DIR, "sample_products.csv")
    sales_path = os.path.join(DATA_DIR, "sample_sales.csv")
    if not (os.path.exists(products_path) and os.path.exists(sales_path)):
        raise FileNotFoundError(
            "No sample data found. Run `python ml/data/generate_sample_data.py` first, "
            "or connect a Django database with real sales history."
        )
    products_df = pd.read_csv(products_path)
    sales_df = pd.read_csv(sales_path)
    sales_df["date"] = pd.to_datetime(sales_df["date"])

    frames = []
    for _, prow in products_df.iterrows():
        product_sales = sales_df[sales_df["product_id"] == prow["sku"]][["date", "quantity_sold"]]
        records = product_sales.to_dict("records")
        product = _fake_product(prow)
        df = build_training_frame(records, product, horizon_days=HORIZON_DAYS)
        if df is not None and len(df) > 20:
            df["sku"] = prow["sku"]
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


def train_stockout_model(persist_metrics=True):
    os.makedirs(MODELS_DIR, exist_ok=True)
    df, source = load_training_data()
    if df is None or df.empty:
        raise ValueError("No training data available for the stockout model.")

    X = df[FEATURE_COLUMNS].astype(float)
    y = df[CLASSIFICATION_TARGET].astype(int)

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y if y.nunique() > 1 else None
    )

    scaler = StandardScaler()
    X_train_s = scaler.fit_transform(X_train)
    X_test_s = scaler.transform(X_test)

    candidates = {
        "LogisticRegression": LogisticRegression(max_iter=1000, class_weight="balanced"),
        "RandomForest": RandomForestClassifier(
            n_estimators=300, max_depth=8, min_samples_leaf=5,
            class_weight="balanced", random_state=42, n_jobs=-1,
        ),
    }
    if HAS_XGBOOST:
        candidates["XGBoost"] = xgb.XGBClassifier(
            n_estimators=300, max_depth=5, learning_rate=0.05,
            eval_metric="logloss", random_state=42,
        )

    results = {}
    for name, model in candidates.items():
        model.fit(X_train_s, y_train)
        preds = model.predict(X_test_s)
        proba = model.predict_proba(X_test_s)[:, 1] if hasattr(model, "predict_proba") else preds

        metrics = {
            "accuracy": round(accuracy_score(y_test, preds), 4),
            "precision": round(precision_score(y_test, preds, zero_division=0), 4),
            "recall": round(recall_score(y_test, preds, zero_division=0), 4),
            "f1_score": round(f1_score(y_test, preds, zero_division=0), 4),
            "roc_auc": round(roc_auc_score(y_test, proba), 4) if y_test.nunique() > 1 else None,
            "confusion_matrix": confusion_matrix(y_test, preds).tolist(),
        }
        results[name] = {"model": model, "metrics": metrics}

    best_name = max(results, key=lambda n: (results[n]["metrics"]["f1_score"] or 0))
    best_model = results[best_name]["model"]

    joblib.dump(best_model, os.path.join(MODELS_DIR, "stockout_model.pkl"))
    joblib.dump(scaler, os.path.join(MODELS_DIR, "stockout_scaler.pkl"))
    joblib.dump(FEATURE_COLUMNS, os.path.join(MODELS_DIR, "stockout_features.pkl"))

    summary = {
        "best_model": best_name,
        "data_source": source,
        "training_samples": int(len(df)),
        "all_results": {n: r["metrics"] for n, r in results.items()},
    }
    with open(os.path.join(MODELS_DIR, "stockout_model_metrics.json"), "w") as f:
        json.dump(summary, f, indent=2, default=str)

    if persist_metrics:
        try:
            from apps.predictions.models import ModelPerformance
            ModelPerformance.objects.filter(model_type="CLASSIFICATION").update(is_active=False)
            for name, r in results.items():
                ModelPerformance.objects.create(
                    model_type="CLASSIFICATION", model_name=name, metrics_json=r["metrics"],
                    is_active=(name == best_name), training_samples=len(df),
                )
        except Exception:
            pass

    return summary


if __name__ == "__main__":
    summary = train_stockout_model(persist_metrics=False)
    print(json.dumps(summary, indent=2, default=str))
