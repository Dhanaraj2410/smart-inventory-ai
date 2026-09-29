from datetime import date, timedelta
from django.test import TestCase
from apps.accounts.models import User
from apps.products.models import Product
from apps.sales.models import SalesRecord
from apps.recommendations.services import average_daily_sales, calculate_reorder


class ReorderCalculationTests(TestCase):
    def setUp(self):
        self.product = Product.objects.create(
            sku="TEST-001", name="Test Widget", current_stock=50,
            minimum_stock=20, maximum_stock=500, safety_stock=20, supplier_lead_time=5,
            unit_price=10,
        )
        today = date.today()
        for i in range(30):
            SalesRecord.objects.create(
                product=self.product, date=today - timedelta(days=i),
                quantity_sold=10, unit_price=10,
            )

    def test_average_daily_sales(self):
        avg = average_daily_sales(self.product, window_days=30)
        self.assertGreater(avg, 0)

    def test_average_daily_sales_ignores_future_records(self):
        SalesRecord.objects.create(
            product=self.product, date=date.today() + timedelta(days=1),
            quantity_sold=1000, unit_price=10,
        )

        self.assertEqual(average_daily_sales(self.product, window_days=30), 10)

    def test_average_daily_sales_uses_exact_window(self):
        SalesRecord.objects.create(
            product=self.product, date=date.today() - timedelta(days=7),
            quantity_sold=1000, unit_price=10,
        )

        self.assertEqual(average_daily_sales(self.product, window_days=7), 10)

    def test_reorder_point_formula(self):
        """Reorder point = avg_daily_demand * lead_time + safety_stock."""
        result = calculate_reorder(self.product)
        expected = round(result["average_daily_demand"] * self.product.supplier_lead_time
                          + self.product.safety_stock, 2)
        self.assertEqual(result["reorder_point"], expected)

    def test_reorder_required_when_below_point(self):
        self.product.current_stock = 1
        self.product.save()
        result = calculate_reorder(self.product)
        self.assertTrue(result["reorder_required"])

    def test_reorder_not_required_when_well_stocked(self):
        self.product.current_stock = 100000
        self.product.save()
        result = calculate_reorder(self.product)
        self.assertFalse(result["reorder_required"])

    def test_simulation_demand_increase_raises_recommended_quantity(self):
        baseline = calculate_reorder(self.product)
        simulated = calculate_reorder(self.product, demand_increase_pct=50)
        self.assertGreaterEqual(simulated["recommended_quantity"], baseline["recommended_quantity"])
