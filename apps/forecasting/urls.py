from django.urls import path
from . import views

app_name = "forecasting"

urlpatterns = [
    path("<int:pk>/", views.forecast_detail, name="detail"),
]
