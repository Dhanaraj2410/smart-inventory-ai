from django.db import models
from apps.products.models import Product


class ReorderRecommendation(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="reorder_recommendations")

    average_daily_demand = models.FloatField()
    supplier_lead_time = models.PositiveIntegerField()
    safety_stock = models.IntegerField()
    reorder_point = models.FloatField()
    forecast_demand = models.FloatField(help_text="Forecasted demand used for the reorder qty calc")

    current_stock = models.IntegerField()
    recommended_quantity = models.IntegerField()
    reorder_required = models.BooleanField(default=False)

    explanation = models.TextField(blank=True)
    is_simulation = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["product", "-created_at"])]

    def __str__(self):
        tag = "SIM" if self.is_simulation else "LIVE"
        return f"[{tag}] {self.product.sku} -> {self.recommended_quantity} units"
