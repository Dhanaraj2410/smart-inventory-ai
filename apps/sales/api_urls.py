from rest_framework.routers import DefaultRouter
from .api_views import SalesRecordViewSet

router = DefaultRouter()
router.register("sales", SalesRecordViewSet, basename="sales")
urlpatterns = router.urls
