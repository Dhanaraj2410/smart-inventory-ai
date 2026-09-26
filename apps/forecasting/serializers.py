from rest_framework import serializers
from .models import DemandForecast


class DemandForecastSerializer(serializers.ModelSerializer):
    product_sku = serializers.CharField(source="product.sku", read_only=True)
    total_forecast = serializers.FloatField(read_only=True)

    class Meta:
        model = DemandForecast
        fields = ["id", "product", "product_sku", "horizon_days", "values_json",
                  "total_forecast", "model_name", "generated_at"]
