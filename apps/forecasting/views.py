from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404

from apps.products.models import Product
from .services import run_forecast


@login_required
def forecast_detail(request, pk):
    product = get_object_or_404(Product, pk=pk)
    horizon = int(request.GET.get("horizon", 7))
    forecast = run_forecast(product, horizon_days=horizon, persist=True)
    return render(request, "forecasting/detail.html", {
        "product": product, "forecast": forecast, "horizon": horizon,
    })
