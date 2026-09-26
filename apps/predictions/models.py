from django.db import models
from apps.products.models import Product


class PredictionHistory(models.Model):
    class RiskLevel(models.TextChoices):
        LOW = "LOW", "Low"
        MEDIUM = "MEDIUM", "Medium"
        HIGH = "HIGH", "High"

    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="risk_predictions")
    risk_level = models.CharField(max_length=10, choices=RiskLevel.choices)
    probability = models.FloatField(help_text="Model probability of stockout, 0-1")
    horizon_days = models.PositiveIntegerField(default=7)
    factors_json = models.JSONField(default=list, blank=True,
                                     help_text="Top contributing factors, most important first")
    model_name = models.CharField(max_length=100, default="RandomForestClassifier")
    predicted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-predicted_at"]
        indexes = [models.Index(fields=["product", "-predicted_at"]), models.Index(fields=["risk_level"])]

    def __str__(self):
        return f"{self.product.sku} | {self.risk_level} ({self.probability:.0%})"


class ModelPerformance(models.Model):
    class ModelType(models.TextChoices):
        CLASSIFICATION = "CLASSIFICATION", "Stockout Classification"
        REGRESSION = "REGRESSION", "Demand Forecasting"

    model_type = models.CharField(max_length=20, choices=ModelType.choices)
    model_name = models.CharField(max_length=100)
    metrics_json = models.JSONField(default=dict)
    is_active = models.BooleanField(default=False)
    trained_at = models.DateTimeField(auto_now_add=True)
    training_samples = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["-trained_at"]

    def __str__(self):
        return f"{self.model_name} ({self.model_type}) @ {self.trained_at:%Y-%m-%d %H:%M}"


class InventoryAlert(models.Model):
    class AlertType(models.TextChoices):
        HIGH_RISK = "HIGH_RISK", "High Stockout Risk"
        OUT_OF_STOCK = "OUT_OF_STOCK", "Out of Stock"
        BELOW_REORDER_POINT = "BELOW_REORDER_POINT", "Below Reorder Point"
        OVERSTOCK = "OVERSTOCK", "Overstock"
        DEMAND_SPIKE = "DEMAND_SPIKE", "Unexpected Demand Increase"

    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="alerts")
    alert_type = models.CharField(max_length=30, choices=AlertType.choices)
    message = models.CharField(max_length=500)
    is_resolved = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    resolved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["alert_type", "is_resolved"])]

    def __str__(self):
        return f"{self.get_alert_type_display()}: {self.product.sku}"
