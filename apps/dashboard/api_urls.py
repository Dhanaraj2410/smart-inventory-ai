from django.urls import path
from .api_views import dashboard_api

urlpatterns = [
    path("dashboard/", dashboard_api, name="dashboard-api"),
]
