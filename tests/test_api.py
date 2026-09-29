"""API-level tests: product, prediction, forecast, recommendation, and AI endpoints."""
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status

from apps.accounts.models import User
from apps.products.models import Product


class APITestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.admin = User.objects.create_user(
            username="admin", password="testpass123", role=User.Role.ADMIN, is_staff=True,
        )
        self.viewer = User.objects.create_user(
            username="viewer", password="testpass123", role=User.Role.VIEWER,
        )
        self.product = Product.objects.create(
            sku="API-001", name="API Test Product", current_stock=50,
            minimum_stock=10, maximum_stock=200, safety_stock=10, supplier_lead_time=5,
            unit_price="12.00",
        )

    def test_product_list_requires_auth(self):
        resp = self.client.get("/api/products/")
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_product_list_authenticated(self):
        self.client.force_authenticate(self.viewer)
        resp = self.client.get("/api/products/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_viewer_cannot_create_product(self):
        self.client.force_authenticate(self.viewer)
        resp = self.client.post("/api/products/", {"sku": "NEW-1", "name": "New", "current_stock": 1})
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_can_create_product(self):
        self.client.force_authenticate(self.admin)
        resp = self.client.post("/api/products/", {
            "sku": "NEW-2", "name": "New Product", "current_stock": 5,
            "minimum_stock": 1, "maximum_stock": 100, "safety_stock": 5,
            "supplier_lead_time": 3, "unit_price": "5.00",
        })
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)

    def test_product_maximum_stock_cannot_be_below_minimum_stock(self):
        self.client.force_authenticate(self.admin)
        resp = self.client.patch(
            f"/api/products/{self.product.id}/",
            {"minimum_stock": 10, "maximum_stock": 0},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_prediction_endpoint(self):
        self.client.force_authenticate(self.viewer)
        resp = self.client.get(f"/api/predict/{self.product.id}/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertIn("risk_level", resp.data)

    def test_prediction_endpoint_returns_404_for_unknown_product(self):
        self.client.force_authenticate(self.viewer)
        resp = self.client.get("/api/predict/999999/")
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_recommendation_bulk_endpoint(self):
        self.client.force_authenticate(self.viewer)
        resp = self.client.get("/api/recommendations/bulk/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_ai_chat_grounded_no_data_response(self):
        self.client.force_authenticate(self.viewer)
        resp = self.client.post("/api/ai/chat/", {"message": "How many unicorns do we have in stock?"})
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertIn("couldn't find", resp.data["answer"].lower())
