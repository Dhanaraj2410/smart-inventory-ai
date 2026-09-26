from django.db import models
from apps.products.models import Product


class DemandForecast(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="demand_forecasts")
    horizon_days = models.PositiveIntegerField()
    values_json = models.JSONField(help_text="List of predicted units for day 1..N")
    model_name = models.CharField(max_length=100, default="RandomForestRegressor")
    generated_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-generated_at"]
        indexes = [models.Index(fields=["product", "horizon_days", "-generated_at"])]

    @property
    def total_forecast(self):
        return round(sum(self.values_json), 2)

    def __str__(self):
        return f"{self.product.sku} | {self.horizon_days}d forecast ({self.generated_at:%Y-%m-%d})"
