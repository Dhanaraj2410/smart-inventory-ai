from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("apps.dashboard.urls")),
    path("accounts/", include("apps.accounts.urls")),
    path("products/", include("apps.products.urls")),
    path("sales/", include("apps.sales.urls")),
    path("predictions/", include("apps.predictions.urls")),
    path("forecasts/", include("apps.forecasting.urls")),
    path("recommendations/", include("apps.recommendations.urls")),
    path("ai/", include("apps.ai_assistant.urls")),
    path("reports/", include("apps.reports.urls")),

    # REST API
    path("api/", include("apps.products.api_urls")),
    path("api/", include("apps.sales.api_urls")),
    path("api/", include("apps.predictions.api_urls")),
    path("api/", include("apps.forecasting.api_urls")),
    path("api/", include("apps.recommendations.api_urls")),
    path("api/", include("apps.dashboard.api_urls")),
    path("api/", include("apps.ai_assistant.api_urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
