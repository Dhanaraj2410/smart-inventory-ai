from django.db import models
from django.core.validators import MinValueValidator
from apps.products.models import Product, Warehouse


class SalesRecord(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="sales_records")
    date = models.DateField(db_index=True)
    quantity_sold = models.PositiveIntegerField()
    unit_price = models.DecimalField(
        max_digits=10, decimal_places=2, validators=[MinValueValidator(0)]
    )
    warehouse = models.ForeignKey(Warehouse, on_delete=models.SET_NULL, null=True, blank=True,
                                   related_name="sales_records")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-date"]
        indexes = [
            models.Index(fields=["product", "date"]),
            models.Index(fields=["date"]),
        ]

    @property
    def revenue(self):
        return round(float(self.quantity_sold) * float(self.unit_price), 2)

    def __str__(self):
        return f"{self.product.sku} | {self.date} | {self.quantity_sold} units"


class SalesImportLog(models.Model):
    file_name = models.CharField(max_length=255)
    rows_processed = models.PositiveIntegerField(default=0)
    rows_created = models.PositiveIntegerField(default=0)
    rows_failed = models.PositiveIntegerField(default=0)
    errors = models.TextField(blank=True)
    uploaded_by = models.ForeignKey("accounts.User", on_delete=models.SET_NULL, null=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-uploaded_at"]

    def __str__(self):
        return f"{self.file_name} ({self.uploaded_at:%Y-%m-%d %H:%M})"
