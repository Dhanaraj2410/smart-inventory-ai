from unittest.mock import patch

from django.test import TestCase
from django.urls import reverse

from apps.accounts.models import User
from apps.products.models import Product


class DemandForecastReportTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="report-user", password="test-password")
        self.client.force_login(self.user)
        self.product = Product.objects.create(sku="REPORT-001", name="Report Product")

    @patch("apps.forecasting.services.run_forecast", return_value={"values": [3.0, 4.0]})
    def test_report_builder_includes_demand_forecast_section(self, run_forecast):
        response = self.client.get(
            reverse("reports:generate"),
            {"section": "demand_forecast"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "DEMAND_FORECAST")
        self.assertContains(response, "REPORT-001")
        self.assertContains(response, "[3.0, 4.0]")
        run_forecast.assert_called_once_with(self.product, horizon_days=7, persist=False)
