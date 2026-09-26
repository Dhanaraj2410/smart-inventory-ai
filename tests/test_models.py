"""Model-level tests: product creation, inventory calculation, reorder calculation."""
from datetime import date, timedelta

from django.test import TestCase

from apps.products.models import Product, Category
from apps.sales.models import SalesRecord
from apps.recommendations.services import calculate_reorder, average_daily_sales


class ProductModelTests(TestCase):
    def setUp(self):
        self.category = Category.objects.create(name="Electronics")
        self.product = Product.objects.create(
            sku="TST-001", name="Test Widget", category=self.category,
            current_stock=50, minimum_stock=20, maximum_stock=200,
            safety_stock=10, supplier_lead_time=5, unit_price="9.99",
        )

    def test_product_creation(self):
        self.assertEqual(Product.objects.count(), 1)
        self.assertEqual(self.product.sku, "TST-001")

    def test_inventory_value(self):
        self.assertAlmostEqual(self.product.inventory_value, 50 * 9.99, places=2)

    def test_stock_status_out_of_stock(self):
        self.product.current_stock = 0
        self.product.save()
        self.assertEqual(self.product.stock_status, "OUT_OF_STOCK")

    def test_stock_status_overstocked(self):
        self.product.current_stock = 999
        self.product.save()
        self.assertEqual(self.product.stock_status, "OVERSTOCKED")

    def test_stock_status_critical(self):
        self.product.current_stock = 15  # <= minimum_stock (20)
        self.product.save()
        self.assertEqual(self.product.stock_status, "CRITICAL")


class ReorderCalculationTests(TestCase):
    def setUp(self):
        self.product = Product.objects.create(
            sku="TST-002", name="Reorder Widget", current_stock=40,
            minimum_stock=20, maximum_stock=500, safety_stock=20,
            supplier_lead_time=5, unit_price="19.99",
        )
        today = date.today()
        for i in range(30):
            SalesRecord.objects.create(
                product=self.product, date=today - timedelta(days=i),
                quantity_sold=10, unit_price="19.99",
            )

    def test_average_daily_sales(self):
        avg = average_daily_sales(self.product, window_days=30)
        self.assertGreater(avg, 0)

    def test_reorder_point_formula(self):
        result = calculate_reorder(self.product)
        expected_reorder_point = round(
            result["average_daily_demand"] * self.product.supplier_lead_time + self.product.safety_stock, 2
        )
        self.assertEqual(result["reorder_point"], expected_reorder_point)

    def test_reorder_required_flag(self):
        result = calculate_reorder(self.product)
        self.assertEqual(result["reorder_required"], self.product.current_stock <= result["reorder_point"])

    def test_simulation_does_not_persist_by_default(self):
        from apps.recommendations.models import ReorderRecommendation
        calculate_reorder(self.product, demand_increase_pct=50, is_simulation=True)
        self.assertEqual(ReorderRecommendation.objects.count(), 0)
