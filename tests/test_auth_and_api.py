from django.test import TestCase, Client
from django.urls import reverse
from apps.accounts.models import User
from apps.products.models import Product


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
