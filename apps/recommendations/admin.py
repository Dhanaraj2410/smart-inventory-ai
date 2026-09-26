from django.contrib import admin
from .models import ReorderRecommendation


@admin.register(ReorderRecommendation)
class ReorderRecommendationAdmin(admin.ModelAdmin):
    list_display = ("product", "recommended_quantity", "reorder_required", "is_simulation", "created_at")
    list_filter = ("reorder_required", "is_simulation")
    search_fields = ("product__sku", "product__name")
