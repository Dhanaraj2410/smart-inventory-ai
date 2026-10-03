from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.shortcuts import render, get_object_or_404, redirect
from django.utils import timezone
from django.views.decorators.http import require_POST
from kombu.exceptions import OperationalError
import logging

from apps.accounts.permissions import role_required
from apps.accounts.models import User
from apps.products.models import Product
from .models import PredictionHistory, ModelPerformance, InventoryAlert
from .services import run_prediction, bulk_predict

logger = logging.getLogger(__name__)


@login_required
def prediction_list(request):
    results = bulk_predict(persist=False)
    results.sort(key=lambda r: -r["probability"])
    return render(request, "predictions/list.html", {"results": results})


@login_required
def model_performance(request):
    performances = ModelPerformance.objects.all()[:20]
    return render(request, "predictions/performance.html", {"performances": performances})


@login_required
def alert_list(request):
    alerts = InventoryAlert.objects.select_related("product").filter(is_resolved=False)
    return render(request, "predictions/alerts.html", {"alerts": alerts})


@login_required
@role_required(User.Role.ADMIN, User.Role.MANAGER)
@require_POST
def resolve_alert(request, pk):
    alert = get_object_or_404(InventoryAlert, pk=pk)
    alert.is_resolved = True
    alert.resolved_at = timezone.now()
    alert.save(update_fields=["is_resolved", "resolved_at"])
    return redirect("predictions:alerts")


@login_required
@role_required(User.Role.ADMIN)
def train_models(request):
    """Kicks off model training. Uses Celery if configured/running; otherwise
    runs synchronously so the feature still works without a worker."""
    if request.method == "POST":
        try:
            from apps.predictions.tasks import retrain_models_task
            retrain_models_task.delay()
            messages.success(request, "Model training started in the background.")
        except OperationalError as exc:
            logger.warning("Celery broker unavailable; training models synchronously: %s", exc)
            from ml.training.train_stockout_model import train_stockout_model
            from ml.training.train_demand_model import train_demand_model
            train_stockout_model()
            train_demand_model()
            messages.success(request, "Models trained synchronously (no Celery worker detected).")
        return redirect("predictions:performance")
    return render(request, "predictions/train.html")


@login_required
def bulk_upload_predict(request):
    """CSV bulk prediction: upload a CSV of product_id[/sku] rows and get
    stockout risk + reorder recommendation for each, exportable as CSV."""
    import csv
    import io
    from django.http import HttpResponse
    from apps.recommendations.services import calculate_reorder

    if request.method == "POST":
        f = request.FILES.get("file")
        if not f:
            messages.error(request, "Choose a CSV file to upload.")
            return redirect("predictions:bulk")
        try:
            text = f.read().decode("utf-8-sig")
        except UnicodeDecodeError:
            messages.error(request, "CSV must be encoded as UTF-8.")
            return redirect("predictions:bulk")
        decoded = io.StringIO(text)
        reader = csv.DictReader(decoded)
        if not reader.fieldnames:
            messages.error(request, "CSV must include a header row.")
            return redirect("predictions:bulk")
        headers = [column.strip().lower() for column in reader.fieldnames]
        if len(headers) != len(set(headers)):
            messages.error(request, "CSV contains duplicate column names.")
            return redirect("predictions:bulk")
        if not {"product_id", "sku"}.intersection(headers):
            messages.error(request, "CSV must include a product_id or sku column.")
            return redirect("predictions:bulk")
        reader.fieldnames = headers
        rows = []
        errors = []
        for line_number, row in enumerate(reader, start=2):
            if None in row or any(value is None for value in row.values()):
                errors.append(f"Row {line_number}: unexpected number of columns.")
                continue
            ident = (row.get("product_id") or row.get("sku") or "").strip()
            if not ident:
                errors.append(f"Row {line_number}: product_id or sku is required.")
                continue
            product = Product.objects.filter(sku=ident).first() or \
                (Product.objects.filter(pk=ident).first() if ident.isdigit() else None)
            if not product:
                errors.append(f"Row {line_number}: product '{ident}' was not found.")
                continue
            prediction = run_prediction(product, persist=False)
            reco = calculate_reorder(product)
            rows.append({
                "sku": product.sku, "name": product.name,
                "risk_level": prediction["risk_level"], "probability": prediction["probability"],
                "reorder_required": reco["reorder_required"],
                "recommended_quantity": reco["recommended_quantity"],
            })

        if request.POST.get("export") == "1":
            response = HttpResponse(content_type="text/csv")
            response["Content-Disposition"] = 'attachment; filename="bulk_predictions.csv"'
            writer = csv.writer(response)
            writer.writerow(["sku", "name", "risk_level", "probability",
                              "reorder_required", "recommended_quantity"])
            for r in rows:
                writer.writerow([r["sku"], r["name"], r["risk_level"], r["probability"],
                                  r["reorder_required"], r["recommended_quantity"]])
            return response

        return render(request, "predictions/bulk_results.html", {"rows": rows, "errors": errors})

    return render(request, "predictions/bulk_upload.html")
