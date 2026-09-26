from rest_framework import serializers
from .models import SalesRecord


class SalesRecordSerializer(serializers.ModelSerializer):
    product_sku = serializers.CharField(source="product.sku", read_only=True)
    revenue = serializers.FloatField(read_only=True)

    class Meta:
        model = SalesRecord
        fields = ["id", "product", "product_sku", "date", "quantity_sold", "unit_price",
                  "revenue", "warehouse", "created_at"]
