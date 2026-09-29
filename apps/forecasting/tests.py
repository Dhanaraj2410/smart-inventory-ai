from unittest.mock import patch

from django.test import TestCase

from apps.products.models import Product
from apps.forecasting.services import run_forecast


class DemandForecastTests(TestCase):
    def setUp(self):
        self.product = Product.objects.create(
            sku="FORECAST-001",
            name="Forecast Test Product",
            current_stock=20,
        )

    @patch(
        "ml.prediction.predict.predict_demand",
        side_effect=RuntimeError("model unavailable"),
    )
    def test_run_forecast_logs_ml_fallback(self, predict):
        with self.assertLogs("apps.forecasting.services", level="WARNING") as logs:
            result = run_forecast(self.product, horizon_days=3, persist=False)

        self.assertIn("using seasonal fallback", logs.output[0])
        self.assertIn("RuntimeError: model unavailable", logs.output[0])
        self.assertEqual(result["model_name"], "SeasonalNaiveFallback")
        self.assertEqual(len(result["values"]), 3)
