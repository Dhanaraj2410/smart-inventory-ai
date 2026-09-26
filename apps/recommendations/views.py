from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404

from apps.products.models import Product
from .services import build_recommendation, bulk_recommendations


@login_required
def recommendation_list(request):
    recs = bulk_recommendations()
    recs.sort(key=lambda r: (not r["reorder_required"], -r["recommended_quantity"]))
    return render(request, "recommendations/list.html", {"recommendations": recs})


@login_required
def simulate(request, pk):
    product = get_object_or_404(Product, pk=pk)
    result = None
    if request.method == "POST":
        demand_increase_pct = float(request.POST.get("demand_increase_pct") or 0)
        extra_lead_days = int(request.POST.get("extra_lead_days") or 0)
        stock_override = request.POST.get("current_stock_override")
        safety_override = request.POST.get("safety_stock_override")
        result = build_recommendation(
            product, persist=False,
            demand_increase_pct=demand_increase_pct,
            extra_lead_days=extra_lead_days,
            override_current_stock=int(stock_override) if stock_override else None,
            override_safety_stock=int(safety_override) if safety_override else None,
            is_simulation=True,
        )
        baseline = build_recommendation(product, persist=False)
        result["baseline"] = baseline
    else:
        result = {"baseline": build_recommendation(product, persist=False)}
    return render(request, "recommendations/simulate.html", {"product": product, "result": result})
