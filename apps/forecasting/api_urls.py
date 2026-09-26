from django.urls import path
from rest_framework.routers import DefaultRouter
from .api_views import DemandForecastViewSet, forecast_view

router = DefaultRouter()
router.register("forecasts", DemandForecastViewSet, basename="forecast")

urlpatterns = router.urls + [
    path("forecast/<int:pk>/", forecast_view, name="forecast-product"),
]
