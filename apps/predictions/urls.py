from django.urls import path
from . import views

app_name = "predictions"

urlpatterns = [
    path("", views.prediction_list, name="list"),
    path("performance/", views.model_performance, name="performance"),
    path("alerts/", views.alert_list, name="alerts"),
    path("alerts/<int:pk>/resolve/", views.resolve_alert, name="resolve_alert"),
    path("train/", views.train_models, name="train"),
    path("bulk/", views.bulk_upload_predict, name="bulk"),
]
