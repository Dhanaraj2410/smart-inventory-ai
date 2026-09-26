from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from .services import (
    get_dashboard_stats, get_risk_breakdown, get_sales_trend,
    get_category_analysis, get_top_risk_products,
)


@login_required
def home(request):
    context = {
        "stats": get_dashboard_stats(),
        "risk_breakdown": get_risk_breakdown(),
        "sales_trend": get_sales_trend(30),
        "category_analysis": get_category_analysis(),
        "top_risk_products": get_top_risk_products(10),
    }
    return render(request, "dashboard/home.html", context)
