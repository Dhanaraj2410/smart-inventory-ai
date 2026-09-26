"""
Reorder Recommendation Engine.

Reorder Point   = (average_daily_demand * supplier_lead_time) + safety_stock
Recommended Qty = max(0, forecast_demand + safety_stock - current_stock)

Both formulas mirror the spec exactly. `forecast_demand` is pulled from the
demand-forecasting model when available (apps.forecasting), falling back to
average_daily_demand * lead_time so the engine still works before any model
has been trained.
"""
from apps.sales.models import SalesRecord
from .models import ReorderRecommendation


def average_daily_sales(product, window_days=30):
    from django.utils import timezone
    from datetime import timedelta

    since = timezone.now().date() - timedelta(days=window_days)
    qs = SalesRecord.objects.filter(product=product, date__gte=since)
    total = sum(r.quantity_sold for r in qs)
    days = max(1, (timezone.now().date() - since).days)
    return round(total / days, 3) if total else 0.0


def _forecast_demand_over_lead_time(product, lead_time_days):
    """Prefer the trained forecasting model's output; otherwise fall back to
    a simple average-based projection so the engine always returns a number."""
    try:
        from apps.forecasting.services import get_latest_forecast
        forecast = get_latest_forecast(product, horizon=max(7, lead_time_days))
        if forecast and forecast.get("values"):
            return round(sum(forecast["values"][:lead_time_days]), 2)
    except Exception:
        pass
    avg_daily = average_daily_sales(product)
    return round(avg_daily * lead_time_days, 2)


def calculate_reorder(product, *, demand_increase_pct=0.0, extra_lead_days=0,
                       override_current_stock=None, override_safety_stock=None,
                       is_simulation=False):
    """Core recommendation calculation. Pass demand_increase_pct/extra_lead_days
    from the What-If Simulator; leave at 0 for a live/real recommendation."""
    avg_daily = average_daily_sales(product) * (1 + demand_increase_pct / 100.0)
    lead_time = product.supplier_lead_time + extra_lead_days
    safety_stock = override_safety_stock if override_safety_stock is not None else product.safety_stock
    current_stock = override_current_stock if override_current_stock is not None else product.current_stock

    reorder_point = round(avg_daily * lead_time + safety_stock, 2)

    base_forecast = _forecast_demand_over_lead_time(product, lead_time)
    forecast_demand = round(base_forecast * (1 + demand_increase_pct / 100.0), 2)

    recommended_qty = max(0, round(forecast_demand + safety_stock - current_stock))
    reorder_required = current_stock <= reorder_point

    explanation = (
        f"Reorder point = (avg daily demand {avg_daily:.1f} x lead time {lead_time}d) "
        f"+ safety stock {safety_stock} = {reorder_point:.1f} units. "
        f"Current stock is {current_stock}, which is "
        f"{'at or below' if reorder_required else 'above'} the reorder point. "
        f"Recommended order = forecasted demand ({forecast_demand:.1f}) + safety stock "
        f"({safety_stock}) - current stock ({current_stock}) = {recommended_qty} units."
    )

    return {
        "product": product,
        "average_daily_demand": round(avg_daily, 3),
        "supplier_lead_time": lead_time,
        "safety_stock": safety_stock,
        "reorder_point": reorder_point,
        "forecast_demand": forecast_demand,
        "current_stock": current_stock,
        "recommended_quantity": recommended_qty,
        "reorder_required": reorder_required,
        "explanation": explanation,
        "is_simulation": is_simulation,
    }


def build_recommendation(product, persist=True, **overrides):
    data = calculate_reorder(product, **overrides)
    if persist:
        obj = ReorderRecommendation.objects.create(
            product=product,
            average_daily_demand=data["average_daily_demand"],
            supplier_lead_time=data["supplier_lead_time"],
            safety_stock=data["safety_stock"],
            reorder_point=data["reorder_point"],
            forecast_demand=data["forecast_demand"],
            current_stock=data["current_stock"],
            recommended_quantity=data["recommended_quantity"],
            reorder_required=data["reorder_required"],
            explanation=data["explanation"],
            is_simulation=data.get("is_simulation", False),
        )
        data["id"] = obj.id
        data["created_at"] = obj.created_at
    return data


def bulk_recommendations(queryset=None):
    from apps.products.models import Product
    queryset = queryset if queryset is not None else Product.objects.filter(is_active=True)
    return [build_recommendation(p, persist=False) for p in queryset]
