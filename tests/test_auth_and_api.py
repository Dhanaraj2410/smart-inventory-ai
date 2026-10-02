from django.test import TestCase, Client
from django.urls import reverse
from apps.accounts.models import User
from apps.products.models import Product
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
