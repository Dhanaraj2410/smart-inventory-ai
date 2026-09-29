"""
Stockout risk prediction service.

Uses the trained classifier (ml/models/stockout_model.pkl) when available.
Falls back to a transparent rule-based estimate — built from the same
signals the ML model uses (stock-to-demand ratio, lead time, recent growth)
— so the rest of the app works before a model has been trained, and so the
fallback's own reasoning is always inspectable rather than a black box.
"""
import logging

from .models import PredictionHistory

logger = logging.getLogger(__name__)


def _rule_based_risk(product):
    from apps.recommendations.services import average_daily_sales
    avg_daily = average_daily_sales(product, window_days=14)
    days_of_cover = (product.current_stock / avg_daily) if avg_daily > 0 else 999
    lead_time = product.supplier_lead_time

    factors = []
    if avg_daily <= 0:
        probability = 0.05
        factors.append("No recent sales activity recorded")
    else:
        ratio = days_of_cover / max(lead_time, 1)
        probability = max(0.02, min(0.98, 1.4 - ratio))
        if product.current_stock <= product.minimum_stock:
            factors.append("Current stock is at or below the minimum stock level")
            probability = min(0.98, probability + 0.15)
        if days_of_cover < lead_time:
            factors.append(
                f"Only {days_of_cover:.1f} days of stock remain, less than the "
                f"{lead_time}-day supplier lead time"
            )
        recent = average_daily_sales(product, window_days=7)
        older = average_daily_sales(product, window_days=30)
        if older > 0 and recent > older * 1.2:
            growth = (recent - older) / older * 100
            factors.append(f"Recent sales increased by {growth:.0f}% vs the prior average")
            probability = min(0.98, probability + 0.1)
        if lead_time >= 7:
            factors.append(f"Supplier lead time is relatively long ({lead_time} days)")

    if not factors:
        factors.append("Stock levels comfortably exceed projected demand")

    if probability >= 0.66:
        risk = PredictionHistory.RiskLevel.HIGH
    elif probability >= 0.33:
        risk = PredictionHistory.RiskLevel.MEDIUM
    else:
        risk = PredictionHistory.RiskLevel.LOW

    return risk, round(probability, 3), factors[:5]


def run_prediction(product, horizon_days=7, persist=True):
    risk_level, probability, factors, model_name = None, None, None, "RuleBasedFallback"
    try:
        from ml.prediction.predict import predict_stockout_risk
        result = predict_stockout_risk(product, horizon_days)
        if result:
            risk_level, probability, factors = result["risk_level"], result["probability"], result["factors"]
            model_name = "RandomForestClassifier"
    except Exception:
        logger.warning(
            "ML stockout prediction failed for product %s; using rule-based fallback.",
            product.pk,
            exc_info=True,
        )

    if risk_level is None:
        risk_level, probability, factors = _rule_based_risk(product)

    if persist:
        return PredictionHistory.objects.create(
            product=product, risk_level=risk_level, probability=probability,
            horizon_days=horizon_days, factors_json=factors, model_name=model_name,
        )
    return {"risk_level": risk_level, "probability": probability, "factors": factors, "model_name": model_name}


def get_latest_risk(product, horizon_days=7, max_age_minutes=60):
    from django.utils import timezone
    from datetime import timedelta

    cutoff = timezone.now() - timedelta(minutes=max_age_minutes)
    existing = PredictionHistory.objects.filter(
        product=product, horizon_days=horizon_days, predicted_at__gte=cutoff
    ).first()
    if existing:
        return existing
    return run_prediction(product, horizon_days=horizon_days, persist=True)


def bulk_predict(queryset=None, horizon_days=7, persist=False):
    from apps.products.models import Product
    queryset = queryset if queryset is not None else Product.objects.filter(is_active=True)
    results = []
    for p in queryset:
        r = run_prediction(p, horizon_days=horizon_days, persist=persist)
        if persist:
            results.append({"product": p, "risk_level": r.risk_level, "probability": r.probability,
                             "factors": r.factors_json})
        else:
            r["product"] = p
            results.append(r)
    return results
