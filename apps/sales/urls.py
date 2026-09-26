from django.urls import path
from . import views

app_name = "sales"

urlpatterns = [
    path("", views.sales_list, name="list"),
    path("upload/", views.sales_upload, name="upload"),
]
