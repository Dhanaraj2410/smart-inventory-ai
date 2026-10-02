"""
Demand forecasting service.

Uses the trained regression model (ml/models/demand_forecasting_model.pkl)
when available. If no model has been trained yet, falls back to a
seasonally-naive projection built from recent sales history so the rest of
the app (recommendations, dashboard, product detail) keeps working end to
end before the ML pipeline has been run.
"""
import logging

import numpy as np

from apps.sales.models import SalesRecord
from .models import DemandForecast

logger = logging.getLogger(__name__)


def _fallback_forecast(product, horizon_days):
    from django.utils import timezone
    from datetime import timedelta

    today = timezone.localdate()
    since = today - timedelta(days=28)
    records = list(SalesRecord.objects.filter(
        product=product, date__gte=since, date__lte=today,
    ).order_by("date"))
    if not records:
        return [0.0] * horizon_days
    by_dow = {i: [] for i in range(7)}
    for r in records:
        by_dow[r.date.weekday()].append(r.quantity_sold)
    dow_avg = {k: (sum(v) / len(v) if v else 0.0) for k, v in by_dow.items()}
    overall_avg = sum(dow_avg.values()) / 7 or 1.0
    values = []
    for i in range(1, horizon_days + 1):
        d = today + timedelta(days=i)
        base = dow_avg.get(d.weekday(), overall_avg)
        values.append(round(max(0.0, base), 2))
    return values


def run_forecast(product, horizon_days=7, persist=True):
    values = None
    try:
        from ml.prediction.predict import predict_demand
        values = predict_demand(product, horizon_days)
    except Exception:
        logger.warning(
            "ML demand forecast failed for product %s; using seasonal fallback.",
            product.pk,
            exc_info=True,
        )
        values = None

    if not values:
        values = _fallback_forecast(product, horizon_days)
        model_name = "SeasonalNaiveFallback"
    else:
        model_name = "RandomForestRegressor"

    if persist:
        return DemandForecast.objects.create(
            product=product, horizon_days=horizon_days,
            values_json=values, model_name=model_name,
        )
    return {"product": product, "horizon_days": horizon_days, "values": values, "model_name": model_name}


def get_latest_forecast(product, horizon=7):
    existing = DemandForecast.objects.filter(product=product, horizon_days=horizon).first()
    if existing:
        return {"values": existing.values_json, "model_name": existing.model_name,
                "generated_at": existing.generated_at, "horizon_days": horizon}
    result = run_forecast(product, horizon_days=horizon, persist=True)
    return {"values": result.values_json, "model_name": result.model_name,
            "generated_at": result.generated_at, "horizon_days": horizon}
