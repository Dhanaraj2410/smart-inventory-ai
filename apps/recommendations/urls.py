from django.urls import path
from . import views

app_name = "recommendations"

urlpatterns = [
    path("", views.recommendation_list, name="list"),
    path("<int:pk>/simulate/", views.simulate, name="simulate"),
]
