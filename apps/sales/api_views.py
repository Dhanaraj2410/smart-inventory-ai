from rest_framework import viewsets, filters
from django_filters.rest_framework import DjangoFilterBackend
from apps.accounts.permissions import ReadOnlyOrManager
from .models import SalesRecord
from .serializers import SalesRecordSerializer


class SalesRecordViewSet(viewsets.ModelViewSet):
    queryset = SalesRecord.objects.select_related("product").all()
    serializer_class = SalesRecordSerializer
    permission_classes = [ReadOnlyOrManager]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ["product", "warehouse", "date"]
    ordering_fields = ["date", "quantity_sold"]
