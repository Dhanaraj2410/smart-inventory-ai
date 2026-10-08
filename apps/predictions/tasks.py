"""Celery background tasks: scheduled inventory-alert checks & bulk model runs."""
import logging
import smtplib

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task
def check_inventory_alerts():
    """Runs on a schedule (see CELERY_BEAT_SCHEDULE). Evaluates every active
    product against alert rules and creates/refreshes InventoryAlert rows."""
    from apps.products.models import Product
    from apps.recommendations.services import calculate_reorder
    from .models import InventoryAlert
    from .services import run_prediction

    created = 0
    for product in Product.objects.filter(is_active=True):
        status = product.stock_status
        if status == "OUT_OF_STOCK":
            _raise_alert(product, InventoryAlert.AlertType.OUT_OF_STOCK,
                         f"{product.name} is out of stock.")
            created += 1
        elif status == "OVERSTOCKED":
            _raise_alert(product, InventoryAlert.AlertType.OVERSTOCK,
                         f"{product.name} is overstocked (current stock {product.current_stock} "
                         f"exceeds maximum {product.maximum_stock}).")
            created += 1

        rec = calculate_reorder(product)
        if rec["reorder_required"]:
            _raise_alert(product, InventoryAlert.AlertType.BELOW_REORDER_POINT,
                         f"{product.name} is below its reorder point "
                         f"({rec['current_stock']} <= {rec['reorder_point']:.0f}).")
            created += 1

        prediction = run_prediction(product, persist=True)
        if prediction.risk_level == "HIGH":
            _raise_alert(product, InventoryAlert.AlertType.HIGH_RISK,
                         f"{product.name} may run out of stock soon "
                         f"(stockout probability {prediction.probability:.0%}).")
            created += 1

    return {"alerts_created_or_refreshed": created}


def _raise_alert(product, alert_type, message):
    from django.core.mail import send_mail
    from django.conf import settings
    from .models import InventoryAlert

    alert, created = InventoryAlert.objects.get_or_create(
        product=product,
        alert_type=alert_type,
        is_resolved=False,
        defaults={"message": message},
    )
    if not created:
        if alert.message != message:
            alert.message = message
            alert.save(update_fields=["message"])
        return

    if settings.EMAIL_HOST:
        try:
            send_mail(
                subject=f"[Smart Inventory AI] {alert_type.replace('_', ' ').title()}",
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[settings.DEFAULT_FROM_EMAIL],
            )
        except (smtplib.SMTPException, OSError):
            logger.exception(
                "Failed to send %s inventory alert email for product %s.",
                alert_type,
                product.pk,
            )


@shared_task
def retrain_models_task():
    """Kicks off a full model retrain in the background (long-running)."""
    from ml.training.train_stockout_model import train_stockout_model
    from ml.training.train_demand_model import train_demand_model
    return {
        "stockout": train_stockout_model(),
        "demand": train_demand_model(),
    }
