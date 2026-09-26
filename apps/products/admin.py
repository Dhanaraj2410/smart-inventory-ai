from django.contrib import admin
from .models import Product, Category, Supplier, Warehouse


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("sku", "name", "category", "supplier", "warehouse", "current_stock",
                     "minimum_stock", "maximum_stock", "stock_status", "is_active")
    list_filter = ("category", "supplier", "warehouse", "is_active")
    search_fields = ("sku", "name")


admin.site.register(Category)
admin.site.register(Supplier)
admin.site.register(Warehouse)
