from django.urls import path
from . import views

app_name = "reports"

urlpatterns = [
    path("", views.report_builder, name="builder"),
    path("generate/", views.generate_report, name="generate"),
]
