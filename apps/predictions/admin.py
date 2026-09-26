from django.contrib import admin
from .models import PredictionHistory, ModelPerformance, InventoryAlert


@admin.register(PredictionHistory)
class PredictionHistoryAdmin(admin.ModelAdmin):
    list_display = ("product", "risk_level", "probability", "horizon_days", "model_name", "predicted_at")
    list_filter = ("risk_level", "model_name")
    search_fields = ("product__sku", "product__name")


@admin.register(ModelPerformance)
class ModelPerformanceAdmin(admin.ModelAdmin):
    list_display = ("model_name", "model_type", "is_active", "training_samples", "trained_at")
    list_filter = ("model_type", "is_active")


@admin.register(InventoryAlert)
class InventoryAlertAdmin(admin.ModelAdmin):
    list_display = ("product", "alert_type", "is_resolved", "created_at")
    list_filter = ("alert_type", "is_resolved")
    search_fields = ("product__sku", "product__name")
