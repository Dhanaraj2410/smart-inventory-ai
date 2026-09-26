from django.contrib import admin
from .models import DemandForecast


@admin.register(DemandForecast)
class DemandForecastAdmin(admin.ModelAdmin):
    list_display = ("product", "horizon_days", "model_name", "generated_at")
    list_filter = ("horizon_days", "model_name")
    search_fields = ("product__sku", "product__name")
