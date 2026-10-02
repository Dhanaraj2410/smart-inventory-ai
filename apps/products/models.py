from django.db import models
from django.urls import reverse
from django.core.validators import MinValueValidator


class Category(models.Model):
    name = models.CharField(max_length=120, unique=True)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = "Categories"
        ordering = ["name"]

    def __str__(self):
        return self.name


class Supplier(models.Model):
    name = models.CharField(max_length=150, unique=True)
    contact_email = models.EmailField(blank=True)
    contact_phone = models.CharField(max_length=30, blank=True)
    average_lead_time_days = models.PositiveIntegerField(default=5)
    reliability_score = models.DecimalField(max_digits=4, decimal_places=2, default=0.9,
                                             help_text="0-1, on-time delivery reliability")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class Warehouse(models.Model):
    name = models.CharField(max_length=120, unique=True)
    location = models.CharField(max_length=200, blank=True)
    capacity_units = models.PositiveIntegerField(default=100000)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class Product(models.Model):
    sku = models.CharField(max_length=40, unique=True)
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, related_name="products")
    supplier = models.ForeignKey(Supplier, on_delete=models.SET_NULL, null=True, related_name="products")
    warehouse = models.ForeignKey(Warehouse, on_delete=models.SET_NULL, null=True, related_name="products")

    current_stock = models.IntegerField(default=0, validators=[MinValueValidator(0)])
    minimum_stock = models.IntegerField(default=10, validators=[MinValueValidator(0)])
    maximum_stock = models.IntegerField(default=500, validators=[MinValueValidator(0)])
    safety_stock = models.IntegerField(default=20, validators=[MinValueValidator(0)])
    supplier_lead_time = models.PositiveIntegerField(default=5, help_text="Days")

    unit_price = models.DecimalField(
        max_digits=10, decimal_places=2, default=0, validators=[MinValueValidator(0)]
    )

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]
        indexes = [
            models.Index(fields=["sku"]),
            models.Index(fields=["name"]),
            models.Index(fields=["category"]),
        ]

    def __str__(self):
        return f"{self.sku} - {self.name}"

    def get_absolute_url(self):
        return reverse("products:detail", kwargs={"pk": self.pk})

    # --- Rule-based inventory health (used as a fast/no-ML fallback and for
    # display; the ML-driven risk classification lives in apps.predictions) ---
    @property
    def reorder_point(self):
        from apps.recommendations.services import average_daily_sales
        avg_daily = average_daily_sales(self)
        return round(avg_daily * self.supplier_lead_time + self.safety_stock, 2)

    @property
    def stock_status(self):
        if self.current_stock <= 0:
            return "OUT_OF_STOCK"
        if self.current_stock > self.maximum_stock:
            return "OVERSTOCKED"
        if self.current_stock <= self.minimum_stock:
            return "CRITICAL"
        if self.current_stock <= self.reorder_point:
            return "LOW_STOCK"
        return "HEALTHY"

    @property
    def inventory_value(self):
        return round(float(self.current_stock) * float(self.unit_price), 2)


STOCK_STATUS_LABELS = {
    "HEALTHY": "Healthy",
    "LOW_STOCK": "Low Stock",
    "CRITICAL": "Critical",
    "OVERSTOCKED": "Overstocked",
    "OUT_OF_STOCK": "Out of Stock",
}
