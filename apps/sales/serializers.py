from rest_framework import serializers
from django.utils import timezone
from .models import SalesRecord


class SalesRecordSerializer(serializers.ModelSerializer):
    product_sku = serializers.CharField(source="product.sku", read_only=True)
    revenue = serializers.FloatField(read_only=True)

    class Meta:
        model = SalesRecord
        fields = ["id", "product", "product_sku", "date", "quantity_sold", "unit_price",
                  "revenue", "warehouse", "created_at"]

    def validate_date(self, value):
        if value > timezone.localdate():
            raise serializers.ValidationError("Sales dates cannot be in the future.")
        return value
