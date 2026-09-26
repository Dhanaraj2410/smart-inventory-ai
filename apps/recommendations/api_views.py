from rest_framework import viewsets
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.accounts.permissions import ReadOnlyOrManager
from apps.products.models import Product
from .models import ReorderRecommendation
from .serializers import ReorderRecommendationSerializer
from .services import build_recommendation, bulk_recommendations


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
    product = Product.objects.get(pk=pk)
    payload = request.data
    result = build_recommendation(
        product, persist=False,
        demand_increase_pct=float(payload.get("demand_increase_pct", 0)),
        extra_lead_days=int(payload.get("extra_lead_days", 0)),
        override_current_stock=payload.get("current_stock_override"),
        override_safety_stock=payload.get("safety_stock_override"),
        is_simulation=True,
    )
    result["product"] = product.sku
    return Response(result)
