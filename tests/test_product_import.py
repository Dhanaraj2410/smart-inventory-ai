from unittest.mock import patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import IntegrityError
from django.test import TestCase
from django.urls import reverse

from apps.accounts.models import User
from apps.products.models import Category, Product, Supplier, Warehouse


class ProductCsvImportTests(TestCase):
    def setUp(self):
        self.manager = User.objects.create_user(
            username="product-import-manager",
            password="test-password",
            role=User.Role.MANAGER,
        )
        self.client.force_login(self.manager)

    def test_import_accepts_case_insensitive_headers(self):
        uploaded_file = SimpleUploadedFile(
            "products.csv",
            b"SKU,Name\nCSV-003,Widget\n",
            content_type="text/csv",
        )

        response = self.client.post(reverse("products:import"), {"file": uploaded_file})

        self.assertEqual(response.status_code, 302)
        self.assertTrue(Product.objects.filter(sku="CSV-003").exists())

    def test_import_rejects_duplicate_headers(self):
        uploaded_file = SimpleUploadedFile(
            "products.csv",
            b"sku,SKU,name\nCSV-004,OTHER,Widget\n",
            content_type="text/csv",
        )

        response = self.client.post(reverse("products:import"), {"file": uploaded_file})

        self.assertEqual(response.status_code, 302)
        self.assertFalse(Product.objects.exists())
        self.assertContains(
            self.client.get(reverse("products:import")),
            "CSV contains duplicate column names",
            status_code=200,
        )

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

    def test_import_rejects_maximum_stock_below_minimum(self):
        uploaded_file = SimpleUploadedFile(
            "products.csv",
            b"sku,name,minimum_stock,maximum_stock\nCSV-002,Widget,10,5\n",
            content_type="text/csv",
        )

        response = self.client.post(reverse("products:import"), {"file": uploaded_file})

        self.assertEqual(response.status_code, 302)
        self.assertFalse(Product.objects.filter(sku="CSV-002").exists())
        self.assertContains(
            self.client.get(reverse("products:import")),
            "maximum_stock cannot be less than minimum_stock",
            status_code=200,
        )

    def test_import_preserves_valid_decimal_unit_price(self):
        uploaded_file = SimpleUploadedFile(
            "products.csv",
            b"sku,name,unit_price\nCSV-005,Widget,12.34\n",
            content_type="text/csv",
        )

        self.client.post(reverse("products:import"), {"file": uploaded_file})

        self.assertEqual(str(Product.objects.get(sku="CSV-005").unit_price), "12.34")

    def test_import_rejects_invalid_unit_prices(self):
        for sku, price in (
            ("CSV-PRICE-1", "NaN"),
            ("CSV-PRICE-2", "Infinity"),
            ("CSV-PRICE-3", "-1.00"),
            ("CSV-PRICE-4", "1.234"),
            ("CSV-PRICE-5", "100000000.00"),
        ):
            with self.subTest(price=price):
                uploaded_file = SimpleUploadedFile(
                    "products.csv",
                    f"sku,name,unit_price\n{sku},Widget,{price}\n".encode(),
                    content_type="text/csv",
                )

                self.client.post(reverse("products:import"), {"file": uploaded_file})

                self.assertFalse(Product.objects.filter(sku=sku).exists())

    def test_import_rejects_blank_sku_and_name(self):
        for row in (",Widget", "CSV-006,   "):
            with self.subTest(row=row):
                uploaded_file = SimpleUploadedFile(
                    "products.csv",
                    f"sku,name\n{row}\n".encode(),
                    content_type="text/csv",
                )

                self.client.post(reverse("products:import"), {"file": uploaded_file})

        self.assertFalse(Product.objects.exists())

    def test_import_rejects_rows_with_extra_columns(self):
        uploaded_file = SimpleUploadedFile(
            "products.csv",
            b"sku,name\nCSV-007,Widget,unexpected\n",
            content_type="text/csv",
        )

        self.client.post(reverse("products:import"), {"file": uploaded_file})

        self.assertFalse(Product.objects.filter(sku="CSV-007").exists())
        self.assertContains(
            self.client.get(reverse("products:import")),
            "unexpected number of columns",
            status_code=200,
        )

    @patch(
        "apps.products.views.Product.objects.update_or_create",
        side_effect=IntegrityError("product write failed"),
    )
    def test_failed_product_write_rolls_back_related_records(self, update_or_create):
        uploaded_file = SimpleUploadedFile(
            "products.csv",
            b"sku,name,category,supplier,warehouse\n"
            b"CSV-008,Widget,New Category,New Supplier,New Warehouse\n",
            content_type="text/csv",
        )

        self.client.post(reverse("products:import"), {"file": uploaded_file})

        self.assertEqual(Category.objects.count(), 0)
        self.assertEqual(Supplier.objects.count(), 0)
        self.assertEqual(Warehouse.objects.count(), 0)
