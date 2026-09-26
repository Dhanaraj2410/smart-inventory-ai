from rest_framework.routers import DefaultRouter
from .api_views import ProductViewSet, CategoryViewSet, SupplierViewSet, WarehouseViewSet

router = DefaultRouter()
router.register("products", ProductViewSet, basename="product")
router.register("categories", CategoryViewSet, basename="category")
router.register("suppliers", SupplierViewSet, basename="supplier")
router.register("warehouses", WarehouseViewSet, basename="warehouse")

urlpatterns = router.urls
