from rest_framework import viewsets, filters
from django_filters.rest_framework import DjangoFilterBackend

from apps.accounts.permissions import ReadOnlyOrManager
from .models import Product, Category, Supplier, Warehouse
from .serializers import ProductSerializer, CategorySerializer, SupplierSerializer, WarehouseSerializer


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
