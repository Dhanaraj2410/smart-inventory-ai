from django.urls import path
from rest_framework.routers import DefaultRouter
from .api_views import (
    PredictionHistoryViewSet, ModelPerformanceViewSet, InventoryAlertViewSet,
    predict_view, bulk_predict_view, train_models_view,
)

router = DefaultRouter()
router.register("predictions", PredictionHistoryViewSet, basename="prediction")
router.register("models/performance", ModelPerformanceViewSet, basename="model-performance")
router.register("alerts", InventoryAlertViewSet, basename="alert")

urlpatterns = router.urls + [
    path("predict/<int:pk>/", predict_view, name="predict-product"),
    path("predictions/bulk/", bulk_predict_view, name="predictions-bulk"),
    path("models/train/", train_models_view, name="models-train"),
]
