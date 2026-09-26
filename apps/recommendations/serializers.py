from rest_framework import serializers
from .models import ReorderRecommendation


class ReorderRecommendationSerializer(serializers.ModelSerializer):
    product_sku = serializers.CharField(source="product.sku", read_only=True)
    product_name = serializers.CharField(source="product.name", read_only=True)

    class Meta:
        model = ReorderRecommendation
        fields = [
            "id", "product", "product_sku", "product_name", "average_daily_demand",
            "supplier_lead_time", "safety_stock", "reorder_point", "forecast_demand",
            "current_stock", "recommended_quantity", "reorder_required", "explanation",
            "is_simulation", "created_at",
        ]
