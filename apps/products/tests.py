from django.test import TestCase
from apps.products.models import Product


class ProductModelTests(TestCase):
    def test_out_of_stock_status(self):
        p = Product.objects.create(sku="A1", name="A", current_stock=0,
                                    minimum_stock=5, maximum_stock=100, safety_stock=5, supplier_lead_time=3)
        self.assertEqual(p.stock_status, "OUT_OF_STOCK")

    def test_overstocked_status(self):
        p = Product.objects.create(sku="A2", name="B", current_stock=200,
                                    minimum_stock=5, maximum_stock=100, safety_stock=5, supplier_lead_time=3)
        self.assertEqual(p.stock_status, "OVERSTOCKED")

    def test_critical_status(self):
        p = Product.objects.create(sku="A3", name="C", current_stock=3,
                                    minimum_stock=5, maximum_stock=100, safety_stock=5, supplier_lead_time=3)
        self.assertEqual(p.stock_status, "CRITICAL")

    def test_inventory_value(self):
        p = Product.objects.create(sku="A4", name="D", current_stock=10, unit_price=2.5,
                                    minimum_stock=1, maximum_stock=100, safety_stock=1, supplier_lead_time=1)
        self.assertEqual(p.inventory_value, 25.0)
