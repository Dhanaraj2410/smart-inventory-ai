from rest_framework import filters, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend

from apps.accounts.permissions import ReadOnlyOrManager
from .models import InventoryAdjustment, Product, Category, Supplier, Warehouse
from .serializers import (
    CategorySerializer,
    InventoryAdjustmentInputSerializer,
    InventoryAdjustmentSerializer,
    ProductSerializer,
    SupplierSerializer,
    WarehouseSerializer,
)
from .services import adjust_inventory


class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.select_related("category", "supplier", "warehouse").filter(is_active=True)
    serializer_class = ProductSerializer
    permission_classes = [ReadOnlyOrManager]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["category", "supplier", "warehouse"]
    search_fields = ["name", "sku"]
    ordering_fields = ["current_stock", "unit_price", "updated_at"]

    def perform_destroy(self, instance):
        instance.is_active = False
        instance.save(update_fields=["is_active"])

    @action(detail=True, methods=["get", "post"], url_path="stock-adjustments")
    def stock_adjustments(self, request, pk=None):
        product = self.get_object()
        if request.method == "GET":
            adjustments = InventoryAdjustment.objects.filter(product=product).select_related(
                "created_by"
            )
            return Response(InventoryAdjustmentSerializer(adjustments, many=True).data)

        input_serializer = InventoryAdjustmentInputSerializer(data=request.data)
        input_serializer.is_valid(raise_exception=True)
        try:
            adjustment = adjust_inventory(
                product.pk,
                input_serializer.validated_data["quantity_change"],
                input_serializer.validated_data["note"],
                request.user,
            )
        except ValueError as exc:
            raise ValidationError({"detail": str(exc)}) from exc
        except Product.DoesNotExist as exc:
            raise NotFound("Product not found.") from exc

        return Response(
            InventoryAdjustmentSerializer(adjustment).data,
            status=status.HTTP_201_CREATED,
        )


class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [ReadOnlyOrManager]


class SupplierViewSet(viewsets.ModelViewSet):
    queryset = Supplier.objects.all()
    serializer_class = SupplierSerializer
    permission_classes = [ReadOnlyOrManager]


class WarehouseViewSet(viewsets.ModelViewSet):
    queryset = Warehouse.objects.all()
    serializer_class = WarehouseSerializer
    permission_classes = [ReadOnlyOrManager]
