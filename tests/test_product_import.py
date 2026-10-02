from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse

from apps.accounts.models import User
from apps.products.models import Product


class ProductCsvImportTests(TestCase):
    def setUp(self):
        self.manager = User.objects.create_user(
            username="product-import-manager",
            password="test-password",
            role=User.Role.MANAGER,
        )
        self.client.force_login(self.manager)

    def test_import_rejects_fractional_stock_without_creating_product(self):
        uploaded_file = SimpleUploadedFile(
            "products.csv",
            b"sku,name,current_stock\nCSV-001,Widget,2.5\n",
            content_type="text/csv",
        )

        response = self.client.post(reverse("products:import"), {"file": uploaded_file})

        self.assertEqual(response.status_code, 302)
        self.assertFalse(Product.objects.filter(sku="CSV-001").exists())
        self.assertContains(
            self.client.get(reverse("products:import")),
            "current_stock must be a non-negative whole number",
            status_code=200,
        )
