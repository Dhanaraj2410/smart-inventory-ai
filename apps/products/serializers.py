from rest_framework import serializers
from .models import InventoryAdjustment, Product, Category, Supplier, Warehouse


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


class InventoryAdjustmentSerializer(serializers.ModelSerializer):
    created_by_username = serializers.CharField(
        source="created_by.username", read_only=True, default=None
    )

    class Meta:
        model = InventoryAdjustment
        fields = [
            "id",
            "product",
            "quantity_change",
            "stock_before",
            "stock_after",
            "note",
            "created_by",
            "created_by_username",
            "created_at",
        ]
        read_only_fields = fields


class InventoryAdjustmentInputSerializer(serializers.Serializer):
    quantity_change = serializers.IntegerField()
    note = serializers.CharField(max_length=500, allow_blank=False, trim_whitespace=True)

    def validate_quantity_change(self, value):
        if value == 0:
            raise serializers.ValidationError("Quantity change cannot be zero.")
        return value

    def validate_note(self, value):
        if not value:
            raise serializers.ValidationError("A note is required for every inventory adjustment.")
        return value


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
        if max_s < min_s:
            raise serializers.ValidationError("maximum_stock cannot be less than minimum_stock.")
        return data
