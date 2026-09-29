from rest_framework import serializers, viewsets
from rest_framework.decorators import api_view, permission_classes
from rest_framework.generics import get_object_or_404
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.accounts.permissions import ReadOnlyOrManager
from apps.products.models import Product
from .models import DemandForecast
from .serializers import DemandForecastSerializer
from .services import run_forecast


class ForecastQuerySerializer(serializers.Serializer):
    horizon = serializers.IntegerField(default=7, min_value=1, max_value=365)


class DemandForecastViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = DemandForecast.objects.select_related("product").all()
    serializer_class = DemandForecastSerializer
    permission_classes = [ReadOnlyOrManager]


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def forecast_view(request, pk):
    product = get_object_or_404(Product, pk=pk)
    query = ForecastQuerySerializer(data=request.query_params)
    query.is_valid(raise_exception=True)
    horizon = query.validated_data["horizon"]
    result = run_forecast(product, horizon_days=horizon, persist=True)
    return Response(DemandForecastSerializer(result).data)
