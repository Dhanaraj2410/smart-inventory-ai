from smtplib import SMTPException
from unittest.mock import patch

from django.test import TestCase, override_settings

from apps.products.models import Product
from apps.predictions.models import InventoryAlert
from apps.predictions.services import run_prediction, _rule_based_risk
from apps.predictions.tasks import _raise_alert


class StockoutPredictionTests(TestCase):
    def setUp(self):
        self.product = Product.objects.create(
            sku="RISK-001", name="Risky Item", current_stock=2,
            minimum_stock=20, maximum_stock=500, safety_stock=20, supplier_lead_time=10,
        )

    def test_rule_based_fallback_returns_valid_risk_level(self):
        risk, probability, factors = _rule_based_risk(self.product)
        self.assertIn(risk, ("LOW", "MEDIUM", "HIGH"))
        self.assertGreaterEqual(probability, 0)
        self.assertLessEqual(probability, 1)
        self.assertIsInstance(factors, list)

    def test_run_prediction_persists_history(self):
        result = run_prediction(self.product, persist=True)
        self.assertEqual(result.product_id, self.product.id)
        self.assertIn(result.risk_level, ("LOW", "MEDIUM", "HIGH"))

    @patch(
        "ml.prediction.predict.predict_stockout_risk",
        side_effect=RuntimeError("model unavailable"),
    )
    def test_run_prediction_logs_ml_fallback(self, predict):
        with self.assertLogs("apps.predictions.services", level="WARNING") as logs:
            result = run_prediction(self.product, persist=False)

        self.assertIn("using rule-based fallback", logs.output[0])
        self.assertIn("RuntimeError: model unavailable", logs.output[0])
        self.assertIn(result["risk_level"], ("LOW", "MEDIUM", "HIGH"))


class InventoryAlertTaskTests(TestCase):
    def setUp(self):
        self.product = Product.objects.create(sku="ALERT-001", name="Alert Item")

    @patch("django.core.mail.send_mail")
    def test_existing_unresolved_alert_message_is_refreshed(self, send_mail):
        alert = InventoryAlert.objects.create(
            product=self.product,
            alert_type=InventoryAlert.AlertType.OUT_OF_STOCK,
            message="Old alert details",
        )

        _raise_alert(self.product, alert.alert_type, "Updated alert details")

        alert.refresh_from_db()
        self.assertEqual(alert.message, "Updated alert details")
        self.assertEqual(InventoryAlert.objects.count(), 1)
        send_mail.assert_not_called()

    @override_settings(EMAIL_HOST="smtp.example.test")
    @patch("django.core.mail.send_mail", side_effect=SMTPException("SMTP unavailable"))
    def test_email_delivery_failure_is_logged_and_alert_is_preserved(self, send_mail):
        with self.assertLogs("apps.predictions.tasks", level="ERROR") as logs:
            _raise_alert(
                self.product,
                InventoryAlert.AlertType.OUT_OF_STOCK,
                "Alert details",
            )

        self.assertEqual(InventoryAlert.objects.count(), 1)
        self.assertIn("Failed to send OUT_OF_STOCK inventory alert email", logs.output[0])
        send_mail.assert_called_once()
