from django.urls import path
from . import views

app_name = "ai_assistant"

urlpatterns = [
    path("chat/", views.chat_view, name="chat_new"),
    path("chat/<int:conversation_id>/", views.chat_view, name="chat"),
    path("insight/<int:pk>/", views.product_insight, name="product_insight"),
]
