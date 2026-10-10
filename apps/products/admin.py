from django.contrib import admin
from .models import InventoryAdjustment, Product, Category, Supplier, Warehouse


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("sku", "name", "category", "supplier", "warehouse", "current_stock",
                     "minimum_stock", "maximum_stock", "stock_status", "is_active")
    list_filter = ("category", "supplier", "warehouse", "is_active")
    search_fields = ("sku", "name")


admin.site.register(Category)
admin.site.register(Supplier)
admin.site.register(Warehouse)


@admin.register(InventoryAdjustment)
class InventoryAdjustmentAdmin(admin.ModelAdmin):
    list_display = (
        "product",
        "quantity_change",
        "stock_before",
        "stock_after",
        "created_by",
        "created_at",
    )
    list_filter = ("created_at",)
    search_fields = ("product__sku", "product__name", "note", "created_by__username")
    readonly_fields = (
        "product",
        "quantity_change",
        "stock_before",
        "stock_after",
        "note",
        "created_by",
        "created_at",
    )

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
