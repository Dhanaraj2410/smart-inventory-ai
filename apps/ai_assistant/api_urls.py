from django.urls import path
from .api_views import chat_api, summary_api, classify_product_api

urlpatterns = [
    path("ai/chat/", chat_api, name="ai-chat"),
    path("ai/summary/", summary_api, name="ai-summary"),
    path("ai/product-insight/", classify_product_api, name="ai-classify"),
]
