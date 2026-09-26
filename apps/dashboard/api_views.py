from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .services import (
    get_dashboard_stats, get_risk_breakdown, get_sales_trend,
    get_category_analysis, get_top_risk_products,
)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def dashboard_api(request):
    return Response({
        "stats": get_dashboard_stats(),
        "risk_breakdown": get_risk_breakdown(),
        "sales_trend": get_sales_trend(int(request.GET.get("days", 30))),
        "category_analysis": get_category_analysis(),
        "top_risk_products": get_top_risk_products(10),
    })
