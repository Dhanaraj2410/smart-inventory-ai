"""
All dashboard numbers are computed live from the database here -- never
hard-coded. This is the single source of truth used by the dashboard page,
the REST API, and the AI assistant's summary feature, so every surface
reports the same numbers.
"""
from django.db.models import Sum, F
from django.utils import timezone
from datetime import timedelta

from apps.products.models import Product
from apps.sales.models import SalesRecord
from apps.predictions.models import PredictionHistory
from apps.recommendations.services import calculate_reorder


def get_dashboard_stats():
    products = list(Product.objects.filter(is_active=True))
    total_products = len(products)
    total_units = sum(p.current_stock for p in products)
    total_inventory_value = round(sum(p.inventory_value for p in products), 2)

    status_counts = {"HEALTHY": 0, "LOW_STOCK": 0, "CRITICAL": 0, "OVERSTOCKED": 0, "OUT_OF_STOCK": 0}
    for p in products:
        status_counts[p.stock_status] += 1

    today = timezone.localdate()
    since_30 = today - timedelta(days=29)
    recent_sales = SalesRecord.objects.filter(date__gte=since_30, date__lte=today)
    total_recent_units = recent_sales.aggregate(s=Sum("quantity_sold"))["s"] or 0
    avg_daily_sales = round(total_recent_units / 30, 2)

    recommended_reorders = sum(1 for p in products if calculate_reorder(p)["reorder_required"])

    latest_risk_by_product = {}
    for pred in PredictionHistory.objects.filter(product__in=products).order_by("product_id", "-predicted_at"):
        latest_risk_by_product.setdefault(pred.product_id, pred.risk_level)
    high_risk = sum(1 for lvl in latest_risk_by_product.values() if lvl == "HIGH")
    predicted_stockouts = high_risk

    return {
        "total_products": total_products,
        "total_units": total_units,
        "total_inventory_value": total_inventory_value,
        "low_stock": status_counts["LOW_STOCK"] + status_counts["CRITICAL"],
        "critical": status_counts["CRITICAL"],
        "overstocked": status_counts["OVERSTOCKED"],
        "out_of_stock": status_counts["OUT_OF_STOCK"],
        "healthy": status_counts["HEALTHY"],
        "high_risk": high_risk,
        "predicted_stockouts": predicted_stockouts,
        "recommended_reorders": recommended_reorders,
        "average_daily_sales": avg_daily_sales,
        "status_breakdown": status_counts,
    }


def get_risk_breakdown():
    products = Product.objects.filter(is_active=True)
    latest_risk_by_product = {}
    for pred in PredictionHistory.objects.filter(product__in=products).order_by("product_id", "-predicted_at"):
        latest_risk_by_product.setdefault(pred.product_id, pred.risk_level)
    counts = {"LOW": 0, "MEDIUM": 0, "HIGH": 0}
    for lvl in latest_risk_by_product.values():
        counts[lvl] = counts.get(lvl, 0) + 1
    return counts


def get_sales_trend(days=30):
    since = timezone.now().date() - timedelta(days=days)
    qs = (SalesRecord.objects.filter(date__gte=since)
          .values("date").annotate(units=Sum("quantity_sold"),
                                    revenue=Sum(F("quantity_sold") * F("unit_price")))
          .order_by("date"))
    return [{"date": r["date"].isoformat(), "units": r["units"] or 0,
              "revenue": float(r["revenue"] or 0)} for r in qs]


def get_category_analysis():
    from apps.products.models import Category
    result = []
    for cat in Category.objects.all():
        products = Product.objects.filter(category=cat, is_active=True)
        units = sum(p.current_stock for p in products)
        value = round(sum(p.inventory_value for p in products), 2)
        recent_sales = SalesRecord.objects.filter(
            product__category=cat, date__gte=timezone.now().date() - timedelta(days=30)
        ).aggregate(s=Sum("quantity_sold"))["s"] or 0
        result.append({"category": cat.name, "units_in_stock": units, "inventory_value": value,
                        "units_sold_30d": recent_sales})
    return result


def get_top_risk_products(limit=10):
    products = Product.objects.filter(is_active=True)
    latest = {}
    for pred in PredictionHistory.objects.filter(product__in=products).order_by("product_id", "-predicted_at"):
        latest.setdefault(pred.product_id, pred)
    ranked = sorted(latest.values(), key=lambda p: -p.probability)[:limit]
    return [{"sku": p.product.sku, "name": p.product.name, "risk_level": p.risk_level,
              "probability": p.probability, "current_stock": p.product.current_stock} for p in ranked]
