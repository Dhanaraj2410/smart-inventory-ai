from rest_framework import serializers, viewsets
from rest_framework.decorators import api_view, permission_classes
from rest_framework.generics import get_object_or_404
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.accounts.permissions import ReadOnlyOrManager
from apps.products.models import Product
from .models import ReorderRecommendation
from .serializers import ReorderRecommendationSerializer
from .services import build_recommendation, bulk_recommendations


class SimulationInputSerializer(serializers.Serializer):
    demand_increase_pct = serializers.FloatField(default=0, min_value=-100)
    extra_lead_days = serializers.IntegerField(default=0, min_value=0, max_value=365)
    current_stock_override = serializers.IntegerField(required=False, min_value=0)
    safety_stock_override = serializers.IntegerField(required=False, min_value=0)


class ReorderRecommendationViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = ReorderRecommendation.objects.select_related("product").all()
    serializer_class = ReorderRecommendationSerializer
    permission_classes = [ReadOnlyOrManager]


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def bulk_recommendations_view(request):
    data = bulk_recommendations()
    for d in data:
        d["product_sku"] = d.pop("product").sku
    return Response(data)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def simulate_view(request, pk):
    product = get_object_or_404(Product, pk=pk)
    payload = SimulationInputSerializer(data=request.data)
    payload.is_valid(raise_exception=True)
    data = payload.validated_data
    result = build_recommendation(
        product, persist=False,
        demand_increase_pct=data["demand_increase_pct"],
        extra_lead_days=data["extra_lead_days"],
        override_current_stock=data.get("current_stock_override"),
        override_safety_stock=data.get("safety_stock_override"),
        is_simulation=True,
    )
    result["product"] = product.sku
    return Response(result)
