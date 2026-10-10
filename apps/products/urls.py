from django.urls import path
from . import views

app_name = "products"

urlpatterns = [
    path("", views.product_list, name="list"),
    path("new/", views.product_create, name="create"),
    path("import/", views.product_import, name="import"),
    path("export/", views.product_export, name="export"),
    path("adjustments/", views.inventory_adjustment_list, name="adjustment_list"),
    path("<int:pk>/", views.product_detail, name="detail"),
    path("<int:pk>/edit/", views.product_edit, name="edit"),
    path("<int:pk>/adjust-stock/", views.product_adjust_stock, name="adjust_stock"),
    path("<int:pk>/delete/", views.product_delete, name="delete"),
]
