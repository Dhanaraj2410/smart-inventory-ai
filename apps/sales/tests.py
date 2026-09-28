from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase

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
