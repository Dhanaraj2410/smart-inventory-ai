from rest_framework import serializers
from .models import PredictionHistory, ModelPerformance, InventoryAlert


class PredictionHistorySerializer(serializers.ModelSerializer):
    product_sku = serializers.CharField(source="product.sku", read_only=True)
    product_name = serializers.CharField(source="product.name", read_only=True)

    class Meta:
        model = PredictionHistory
        fields = ["id", "product", "product_sku", "product_name", "risk_level", "probability",
                  "horizon_days", "factors_json", "model_name", "predicted_at"]


class ModelPerformanceSerializer(serializers.ModelSerializer):
    class Meta:
        model = ModelPerformance
        fields = ["id", "model_type", "model_name", "metrics_json", "is_active",
                  "training_samples", "trained_at"]


class InventoryAlertSerializer(serializers.ModelSerializer):
    product_sku = serializers.CharField(source="product.sku", read_only=True)

    class Meta:
        model = InventoryAlert
        fields = ["id", "product", "product_sku", "alert_type", "message",
                  "is_resolved", "created_at", "resolved_at"]
