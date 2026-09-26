from rest_framework import viewsets
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.accounts.permissions import ReadOnlyOrManager
from apps.products.models import Product
from .models import DemandForecast
from .serializers import DemandForecastSerializer
from .services import run_forecast


class DemandForecastViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = DemandForecast.objects.select_related("product").all()
    serializer_class = DemandForecastSerializer
    permission_classes = [ReadOnlyOrManager]


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def forecast_view(request, pk):
    product = Product.objects.get(pk=pk)
    horizon = int(request.GET.get("horizon", 7))
    result = run_forecast(product, horizon_days=horizon, persist=True)
    return Response(DemandForecastSerializer(result).data)
