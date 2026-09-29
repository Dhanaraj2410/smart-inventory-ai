from rest_framework import viewsets
from rest_framework.decorators import api_view, permission_classes
from rest_framework.generics import get_object_or_404
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.accounts.permissions import ReadOnlyOrManager, IsAdmin
from apps.products.models import Product
from .models import PredictionHistory, ModelPerformance, InventoryAlert
from .serializers import PredictionHistorySerializer, ModelPerformanceSerializer, InventoryAlertSerializer
from .services import run_prediction, bulk_predict


class PredictionHistoryViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = PredictionHistory.objects.select_related("product").all()
    serializer_class = PredictionHistorySerializer
    permission_classes = [ReadOnlyOrManager]


class ModelPerformanceViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = ModelPerformance.objects.all()
    serializer_class = ModelPerformanceSerializer
    permission_classes = [ReadOnlyOrManager]


class InventoryAlertViewSet(viewsets.ModelViewSet):
    queryset = InventoryAlert.objects.select_related("product").all()
    serializer_class = InventoryAlertSerializer
    permission_classes = [ReadOnlyOrManager]


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def predict_view(request, pk):
    product = get_object_or_404(Product, pk=pk)
    horizon = int(request.GET.get("horizon", 7))
    result = run_prediction(product, horizon_days=horizon, persist=True)
    return Response(PredictionHistorySerializer(result).data)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def bulk_predict_view(request):
    results = bulk_predict(persist=False)
    for r in results:
        r["product_sku"] = r.pop("product").sku
    return Response(results)


@api_view(["POST"])
@permission_classes([IsAdmin])
def train_models_view(request):
    try:
        from .tasks import retrain_models_task
        retrain_models_task.delay()
        return Response({"status": "training_started_async"})
    except Exception:
        from ml.training.train_stockout_model import train_stockout_model
        from ml.training.train_demand_model import train_demand_model
        stockout = train_stockout_model()
        demand = train_demand_model()
        return Response({"status": "trained_sync", "stockout": stockout, "demand": demand})
