from unittest.mock import patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.utils import timezone
from datetime import timedelta

from apps.products.models import Product
from apps.sales.models import SalesRecord
from apps.sales.services import validate_and_import_csv


class SalesCsvImportTests(TestCase):
    def setUp(self):
        self.product = Product.objects.create(
            sku="CSV-001",
            name="CSV Test Product",
            current_stock=10,
            minimum_stock=1,
            maximum_stock=100,
            safety_stock=1,
            supplier_lead_time=3,
        )

    def test_import_accepts_whitespace_around_headers(self):
        csv_data = (
            " date , product_id , quantity_sold , unit_price \n"
            "2024-01-01,CSV-001,2,3.50\n"
        )
        uploaded_file = SimpleUploadedFile("sales.csv", csv_data.encode())

        log = validate_and_import_csv(uploaded_file)

        self.assertEqual(log.rows_created, 1)
        self.assertEqual(log.rows_failed, 0)
        self.assertEqual(SalesRecord.objects.get().quantity_sold, 2)

    def test_import_accepts_case_insensitive_headers(self):
        csv_data = (
            "Date,Product_ID,Quantity_Sold,Unit_Price\n"
            "2024-01-01,CSV-001,2,3.50\n"
        )
        uploaded_file = SimpleUploadedFile("sales.csv", csv_data.encode())

        log = validate_and_import_csv(uploaded_file)

        self.assertEqual(log.rows_created, 1)
        self.assertEqual(log.rows_failed, 0)

    def test_import_rejects_duplicate_headers(self):
        csv_data = (
            "date,DATE,product_id,quantity_sold,unit_price\n"
            "2024-01-01,2024-01-02,CSV-001,2,3.50\n"
        )
        uploaded_file = SimpleUploadedFile("sales.csv", csv_data.encode())

        with self.assertRaisesMessage(ValueError, "duplicate column names"):
            validate_and_import_csv(uploaded_file)

    def test_import_rejects_invalid_utf8(self):
        uploaded_file = SimpleUploadedFile("sales.csv", b"\xff\xfe")

        with self.assertRaisesMessage(ValueError, "encoded as UTF-8"):
            validate_and_import_csv(uploaded_file)

        self.assertFalse(SalesRecord.objects.exists())

    def test_import_rejects_fractional_quantities(self):
        csv_data = (
            "date,product_id,quantity_sold,unit_price\n"
            "2024-01-01,CSV-001,2.5,3.50\n"
        )
        uploaded_file = SimpleUploadedFile("sales.csv", csv_data.encode())

        log = validate_and_import_csv(uploaded_file)

        self.assertEqual(log.rows_created, 0)
        self.assertEqual(log.rows_failed, 1)
        self.assertFalse(SalesRecord.objects.exists())

    def test_import_rejects_rows_with_extra_columns(self):
        csv_data = (
            "date,product_id,quantity_sold,unit_price\n"
            "2024-01-01,CSV-001,2,3.50,unexpected\n"
        )
        uploaded_file = SimpleUploadedFile("sales.csv", csv_data.encode())

        log = validate_and_import_csv(uploaded_file)

        self.assertEqual(log.rows_created, 0)
        self.assertEqual(log.rows_failed, 1)
        self.assertIn("unexpected number of columns", log.errors)

    def test_import_rejects_non_finite_prices(self):
        for price in ("NaN", "Infinity", "-Infinity"):
            with self.subTest(price=price):
                csv_data = (
                    "date,product_id,quantity_sold,unit_price\n"
                    f"2024-01-01,CSV-001,2,{price}\n"
                )
                uploaded_file = SimpleUploadedFile("sales.csv", csv_data.encode())

                log = validate_and_import_csv(uploaded_file)

                self.assertEqual(log.rows_created, 0)
                self.assertEqual(log.rows_failed, 1)
        self.assertFalse(SalesRecord.objects.exists())

    def test_import_rejects_prices_outside_database_precision(self):
        for price in ("3.501", "100000000.00"):
            with self.subTest(price=price):
                csv_data = (
                    "date,product_id,quantity_sold,unit_price\n"
                    f"2024-01-01,CSV-001,2,{price}\n"
                )
                uploaded_file = SimpleUploadedFile("sales.csv", csv_data.encode())

                log = validate_and_import_csv(uploaded_file)

                self.assertEqual(log.rows_created, 0)
                self.assertEqual(log.rows_failed, 1)
        self.assertFalse(SalesRecord.objects.exists())

    def test_import_rejects_future_sales_dates(self):
        future_date = (timezone.localdate() + timedelta(days=1)).isoformat()
        csv_data = (
            "date,product_id,quantity_sold,unit_price\n"
            f"{future_date},CSV-001,2,3.50\n"
        )
        uploaded_file = SimpleUploadedFile("sales.csv", csv_data.encode())

        log = validate_and_import_csv(uploaded_file)

        self.assertEqual(log.rows_created, 0)
        self.assertEqual(log.rows_failed, 1)
        self.assertIn("date cannot be in the future", log.errors)

    @patch("apps.sales.services._resolve_product", side_effect=RuntimeError("database unavailable"))
    def test_import_propagates_unexpected_row_processing_errors(self, resolve_product):
        csv_data = (
            "date,product_id,quantity_sold,unit_price\n"
            "2024-01-01,CSV-001,2,3.50\n"
        )
        uploaded_file = SimpleUploadedFile("sales.csv", csv_data.encode())

        with self.assertRaisesMessage(RuntimeError, "database unavailable"):
            validate_and_import_csv(uploaded_file)
