from django.test import TestCase
from unittest.mock import patch
from apps.products.models import Product
from apps.predictions.services import run_prediction, _rule_based_risk


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
