from unittest.mock import patch

from django.test import TestCase, Client
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from kombu.exceptions import OperationalError
from apps.accounts.models import User
from apps.products.models import Product
from apps.predictions.models import InventoryAlert
from apps.sales.models import SalesRecord
from django.utils import timezone
from datetime import timedelta
from apps.dashboard.services import get_sales_trend


class AuthenticationTests(TestCase):
    def setUp(self):
        self.client = Client()

    def test_register_and_login(self):
        resp = self.client.post(reverse("accounts:register"), {
            "username": "newuser", "email": "n@example.com", "role": "VIEWER",
            "password1": "SuperSecret123!", "password2": "SuperSecret123!",
        })
        self.assertEqual(resp.status_code, 302)
        self.assertTrue(User.objects.filter(username="newuser").exists())

    def test_dashboard_requires_login(self):
        resp = self.client.get(reverse("dashboard:home"))
        self.assertEqual(resp.status_code, 302)

    def test_resolving_an_alert_requires_post(self):
        manager = User.objects.create_user(
            username="alert-manager", password="test-password", role=User.Role.MANAGER,
        )
        product = Product.objects.create(sku="ALERT-1", name="Alert Product")
        alert = InventoryAlert.objects.create(
            product=product,
            alert_type=InventoryAlert.AlertType.OUT_OF_STOCK,
            message="Out of stock",
        )
        self.client.force_login(manager)

        response = self.client.get(reverse("predictions:resolve_alert", args=[alert.pk]))

        self.assertEqual(response.status_code, 405)
        alert.refresh_from_db()
        self.assertFalse(alert.is_resolved)

        response = self.client.post(reverse("predictions:resolve_alert", args=[alert.pk]))

        self.assertEqual(response.status_code, 302)
        alert.refresh_from_db()
        self.assertTrue(alert.is_resolved)


class ProductAPITests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="admin1", password="pass12345", role=User.Role.ADMIN)
        self.client = Client()
        self.client.login(username="admin1", password="pass12345")
        self.product = Product.objects.create(sku="API-1", name="API Product", current_stock=5,
                                               minimum_stock=1, maximum_stock=50, safety_stock=1,
                                               supplier_lead_time=2)

    def test_list_products_api(self):
        resp = self.client.get("/api/products/")
        self.assertEqual(resp.status_code, 200)

    def test_dashboard_api_returns_real_stats(self):
        resp = self.client.get("/api/dashboard/")
        self.assertEqual(resp.status_code, 200)
        self.assertIn("stats", resp.json())
        self.assertGreaterEqual(resp.json()["stats"]["total_products"], 1)

    def test_dashboard_average_daily_sales_uses_exact_recent_window(self):
        today = timezone.localdate()
        SalesRecord.objects.create(product=self.product, date=today, quantity_sold=30, unit_price="1.00")
        SalesRecord.objects.create(
            product=self.product, date=today - timedelta(days=30), quantity_sold=300, unit_price="1.00",
        )
        SalesRecord.objects.create(
            product=self.product, date=today + timedelta(days=1), quantity_sold=900, unit_price="1.00",
        )

        response = self.client.get("/api/dashboard/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["stats"]["average_daily_sales"], 1.0)

    def test_sales_trend_uses_exact_window_and_excludes_future_records(self):
        today = timezone.localdate()
        SalesRecord.objects.create(product=self.product, date=today, quantity_sold=10, unit_price="1.00")
        SalesRecord.objects.create(
            product=self.product, date=today - timedelta(days=7), quantity_sold=100, unit_price="1.00",
        )
        SalesRecord.objects.create(
            product=self.product, date=today + timedelta(days=1), quantity_sold=900, unit_price="1.00",
        )

        trend = get_sales_trend(days=7)

        self.assertEqual(trend, [{"date": today.isoformat(), "units": 10, "revenue": 10.0}])

    def test_sales_trend_rejects_non_positive_windows(self):
        with self.assertRaisesMessage(ValueError, "days must be a positive integer"):
            get_sales_trend(days=0)


class BulkPredictionUploadTests(TestCase):
    def setUp(self):
        viewer = User.objects.create_user(
            username="bulk-prediction-viewer",
            password="test-password",
            role=User.Role.VIEWER,
        )
        self.client = Client()
        self.client.force_login(viewer)

    def test_invalid_utf8_upload_shows_validation_message(self):
        uploaded_file = SimpleUploadedFile("products.csv", b"\xff\xfe")

        response = self.client.post(
            reverse("predictions:bulk"),
            {"file": uploaded_file},
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "CSV must be encoded as UTF-8.")

    def test_malformed_rows_are_reported(self):
        uploaded_file = SimpleUploadedFile(
            "products.csv",
            b"sku\nUNKNOWN-1,EXTRA\n",
            content_type="text/csv",
        )

        response = self.client.post(reverse("predictions:bulk"), {"file": uploaded_file})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "unexpected number of columns")


class ModelTrainingViewTests(TestCase):
    def setUp(self):
        admin = User.objects.create_user(
            username="model-training-admin",
            password="test-password",
            role=User.Role.ADMIN,
        )
        self.client = Client()
        self.client.force_login(admin)

    @patch("apps.predictions.tasks.retrain_models_task.delay", side_effect=OperationalError("broker down"))
    @patch("ml.training.train_stockout_model.train_stockout_model")
    @patch("ml.training.train_demand_model.train_demand_model")
    def test_broker_unavailable_runs_synchronous_training(self, train_demand, train_stockout, delay):
        response = self.client.post(reverse("predictions:train"))

        self.assertEqual(response.status_code, 302)
        train_stockout.assert_called_once_with()
        train_demand.assert_called_once_with()

    @patch("apps.predictions.tasks.retrain_models_task.delay", side_effect=RuntimeError("unexpected failure"))
    @patch("ml.training.train_stockout_model.train_stockout_model")
    @patch("ml.training.train_demand_model.train_demand_model")
    def test_unexpected_queue_errors_do_not_start_sync_training(self, train_demand, train_stockout, delay):
        with self.assertRaisesMessage(RuntimeError, "unexpected failure"):
            self.client.post(reverse("predictions:train"))

        train_stockout.assert_not_called()
        train_demand.assert_not_called()
