"""
Retrieval layer for the AI assistant.

Turns a natural-language question into a real Django ORM query and returns
plain-data facts (dicts/lists), which are then handed to
services.huggingface_service.answer_inventory_question() as grounding data.
The Hugging Face layer never talks to the database directly -- this keeps
every number the assistant ever states traceable to an actual query here.
"""
import re

from apps.products.models import Product
from apps.predictions.services import get_latest_risk
from apps.recommendations.services import calculate_reorder


def _product_fact(product, include_prediction=True):
    fact = {
        "sku": product.sku, "name": product.name,
        "category": product.category.name if product.category else None,
        "current_stock": product.current_stock,
        "minimum_stock": product.minimum_stock,
        "maximum_stock": product.maximum_stock,
        "stock_status": product.stock_status,
        "unit_price": float(product.unit_price),
    }
    if include_prediction:
        risk = get_latest_risk(product)
        reco = calculate_reorder(product)
        fact.update({
            "risk_level": risk.risk_level, "probability": risk.probability,
            "reorder_required": reco["reorder_required"],
            "recommended_quantity": reco["recommended_quantity"],
        })
    return fact


def _find_named_product(text):
    text_lower = text.lower()
    candidates = Product.objects.filter(is_active=True)
    for p in candidates:
        if p.sku.lower() in text_lower or p.name.lower() in text_lower:
            return p
    return None


def retrieve_for_question(question):
    """Very lightweight intent routing (regex/keyword based -- deliberately
    simple and inspectable rather than another ML model, since its only job
    is to decide *which real query to run*, not to generate the answer)."""
    q = question.lower()

    named_product = _find_named_product(question)
    if named_product:
        return {"single_product": _product_fact(named_product)}

    if any(k in q for k in ["high risk", "urgent", "high stockout", "critical risk"]):
        qs = [p for p in Product.objects.filter(is_active=True)
              if get_latest_risk(p).risk_level == "HIGH"]
        return {"products": [_product_fact(p) for p in qs[:15]]}

    if "overstock" in q:
        qs = Product.objects.filter(is_active=True)
        qs = [p for p in qs if p.stock_status == "OVERSTOCKED"]
        return {"products": [_product_fact(p, include_prediction=False) for p in qs[:15]]}

    if "out of stock" in q:
        qs = Product.objects.filter(is_active=True, current_stock=0)
        return {"products": [_product_fact(p, include_prediction=False) for p in qs[:15]]}

    if any(k in q for k in ["low stock", "reorder", "restock", "below reorder"]):
        qs = Product.objects.filter(is_active=True)
        results = []
        for p in qs:
            reco = calculate_reorder(p)
            if reco["reorder_required"]:
                fact = _product_fact(p)
                results.append(fact)
        return {"products": results[:15]}

    m = re.search(r"how many ([a-z0-9 \-]+?)(?:\s+in stock|\s+do we have|\?|$)", q)
    if m:
        term = m.group(1).strip()
        matches = Product.objects.filter(is_active=True, name__icontains=term)
        if matches.exists():
            return {"products": [_product_fact(p) for p in matches[:10]]}
        return {"no_match": True, "searched_for": term}

    if any(k in q for k in ["summary", "overview", "how are we doing", "status"]):
        from apps.dashboard.services import get_dashboard_stats
        return {"dashboard_stats": get_dashboard_stats()}

    return {"no_match": True}
