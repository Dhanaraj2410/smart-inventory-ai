"""Inventory-health helpers shared across dashboard, reports, and the AI
assistant's retrieval layer."""
from apps.products.models import Product, STOCK_STATUS_LABELS


def classify_inventory_health(product: Product) -> str:
    return product.stock_status


def inventory_health_counts(queryset=None):
    queryset = queryset if queryset is not None else Product.objects.filter(is_active=True)
    counts = {k: 0 for k in STOCK_STATUS_LABELS}
    for p in queryset:
        counts[p.stock_status] += 1
    return counts
