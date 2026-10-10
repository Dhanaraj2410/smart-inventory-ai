from django.test import TestCase
from django.contrib.auth import get_user_model

from apps.products.models import InventoryAdjustment, Product
from apps.products.services import adjust_inventory


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


class InventoryAdjustmentServiceTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="inventory-manager", password="test-password"
        )
        self.product = Product.objects.create(
            sku="STOCK-1", name="Inventory item", current_stock=10
        )

    def test_adjustment_updates_stock_and_records_audit_values(self):
        adjustment = adjust_inventory(self.product.pk, 5, "Received shipment", self.user)

        self.product.refresh_from_db()
        self.assertEqual(self.product.current_stock, 15)
        self.assertEqual(adjustment.stock_before, 10)
        self.assertEqual(adjustment.stock_after, 15)
        self.assertEqual(adjustment.quantity_change, 5)
        self.assertEqual(adjustment.note, "Received shipment")
        self.assertEqual(adjustment.created_by, self.user)

    def test_negative_adjustment_updates_stock(self):
        adjustment = adjust_inventory(self.product.pk, -4, "Damaged units", self.user)

        self.product.refresh_from_db()
        self.assertEqual(self.product.current_stock, 6)
        self.assertEqual(adjustment.stock_before, 10)
        self.assertEqual(adjustment.stock_after, 6)

    def test_invalid_adjustments_do_not_change_stock_or_create_records(self):
        invalid_adjustments = [
            (0, "Count correction"),
            (-11, "Count correction"),
            (1.5, "Count correction"),
            (1, "  "),
            (1, "x" * 501),
        ]

        for quantity_change, note in invalid_adjustments:
            with self.subTest(quantity_change=quantity_change, note=note[:10]):
                with self.assertRaises(ValueError):
                    adjust_inventory(self.product.pk, quantity_change, note, self.user)

        self.product.refresh_from_db()
        self.assertEqual(self.product.current_stock, 10)
        self.assertEqual(InventoryAdjustment.objects.count(), 0)
