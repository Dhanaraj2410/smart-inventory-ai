from django.contrib import admin
from .models import SalesRecord, SalesImportLog


@admin.register(SalesRecord)
class SalesRecordAdmin(admin.ModelAdmin):
    list_display = ("product", "date", "quantity_sold", "unit_price", "warehouse")
    list_filter = ("warehouse", "date")
    search_fields = ("product__sku", "product__name")


@admin.register(SalesImportLog)
class SalesImportLogAdmin(admin.ModelAdmin):
    list_display = ("file_name", "rows_processed", "rows_created", "rows_failed", "uploaded_at")
