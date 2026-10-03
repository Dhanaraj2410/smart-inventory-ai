from django.test import TestCase
from django.urls import reverse

from apps.accounts.models import User
from apps.products.models import Product


class ProductFormTests(TestCase):
    def setUp(self):
        manager = User.objects.create_user(
            username="product-form-manager",
            password="test-password",
            role=User.Role.MANAGER,
        )
        self.client.force_login(manager)

    def test_invalid_numeric_input_renders_form_errors(self):
        response = self.client.post(reverse("products:create"), {
            "sku": "FORM-001",
            "name": "Form Product",
            "current_stock": "not-a-number",
            "minimum_stock": "1",
            "maximum_stock": "10",
            "safety_stock": "1",
            "supplier_lead_time": "5",
            "unit_price": "1.00",
        })

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Enter a whole number")
        self.assertFalse(Product.objects.filter(sku="FORM-001").exists())

    def test_maximum_stock_cannot_be_below_minimum_stock(self):
        response = self.client.post(reverse("products:create"), {
            "sku": "FORM-002",
            "name": "Form Product",
            "current_stock": "1",
            "minimum_stock": "10",
            "maximum_stock": "5",
            "safety_stock": "1",
            "supplier_lead_time": "5",
            "unit_price": "1.00",
        })

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Maximum stock cannot be less than minimum stock")
        self.assertFalse(Product.objects.filter(sku="FORM-002").exists())

    def test_inactive_product_is_not_available_on_detail_page(self):
        product = Product.objects.create(
            sku="FORM-003",
            name="Archived Product",
            is_active=False,
        )

        response = self.client.get(reverse("products:detail", args=[product.pk]))

        self.assertEqual(response.status_code, 404)
