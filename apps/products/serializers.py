from rest_framework import serializers
from .models import Product, Category, Supplier, Warehouse


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = "__all__"


class SupplierSerializer(serializers.ModelSerializer):
    class Meta:
        model = Supplier
        fields = "__all__"


class WarehouseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Warehouse
        fields = "__all__"


class ProductSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source="category.name", read_only=True, default=None)
    supplier_name = serializers.CharField(source="supplier.name", read_only=True, default=None)
    warehouse_name = serializers.CharField(source="warehouse.name", read_only=True, default=None)
    stock_status = serializers.CharField(read_only=True)
    reorder_point = serializers.FloatField(read_only=True)
    inventory_value = serializers.FloatField(read_only=True)

    class Meta:
        model = Product
        fields = [
            "id", "sku", "name", "description", "category", "category_name",
            "supplier", "supplier_name", "warehouse", "warehouse_name",
            "current_stock", "minimum_stock", "maximum_stock", "safety_stock",
            "supplier_lead_time", "unit_price", "is_active",
            "stock_status", "reorder_point", "inventory_value",
            "created_at", "updated_at",
        ]
        read_only_fields = ["created_at", "updated_at"]

    def validate(self, data):
        min_s = data.get("minimum_stock", getattr(self.instance, "minimum_stock", 0))
        max_s = data.get("maximum_stock", getattr(self.instance, "maximum_stock", 0))
        if max_s and min_s and max_s < min_s:
            raise serializers.ValidationError("maximum_stock cannot be less than minimum_stock.")
        return data
