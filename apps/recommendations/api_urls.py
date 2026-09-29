from django.urls import path
from rest_framework.routers import DefaultRouter
from .api_views import ReorderRecommendationViewSet, bulk_recommendations_view, simulate_view

router = DefaultRouter()
router.register("recommendations", ReorderRecommendationViewSet, basename="recommendation")

urlpatterns = [
    path("recommendations/bulk/", bulk_recommendations_view, name="recommendations-bulk"),
    path("simulation/<int:pk>/", simulate_view, name="simulation"),
] + router.urls
