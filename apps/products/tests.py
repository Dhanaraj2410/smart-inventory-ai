from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.test import Client
from apps.products.forms import InventoryAdjustmentForm
from rest_framework.test import APIClient

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


class InventoryAdjustmentFormTests(TestCase):
    def test_form_accepts_positive_and_negative_adjustments(self):
        for quantity_change in (5, -3):
            with self.subTest(quantity_change=quantity_change):
                form = InventoryAdjustmentForm(
                    {"quantity_change": quantity_change, "note": "Count correction"}
                )
                self.assertTrue(form.is_valid(), form.errors)

    def test_form_rejects_zero_and_missing_note(self):
        form = InventoryAdjustmentForm({"quantity_change": 0, "note": "Count correction"})
        self.assertFalse(form.is_valid())
        self.assertIn("quantity_change", form.errors)

        form = InventoryAdjustmentForm({"quantity_change": 1, "note": ""})
        self.assertFalse(form.is_valid())
        self.assertIn("note", form.errors)


class InventoryAdjustmentViewTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.manager = user_model.objects.create_user(
            username="stock-manager",
            password="test-password",
            role=user_model.Role.MANAGER,
        )
        self.viewer = user_model.objects.create_user(
            username="stock-viewer",
            password="test-password",
            role=user_model.Role.VIEWER,
        )
        self.product = Product.objects.create(
            sku="WEB-1", name="Web inventory item", current_stock=8
        )
        self.url = reverse("products:adjust_stock", args=[self.product.pk])

    def test_manager_can_make_an_adjustment(self):
        self.client.force_login(self.manager)

        response = self.client.post(
            self.url,
            {"quantity_change": "3", "note": "Received shipment"},
        )

        self.assertRedirects(response, reverse("products:detail", args=[self.product.pk]))
        self.product.refresh_from_db()
        self.assertEqual(self.product.current_stock, 11)
        adjustment = InventoryAdjustment.objects.get(product=self.product)
        self.assertEqual(adjustment.created_by, self.manager)

    def test_manager_sees_validation_error_for_adjustment_below_zero(self):
        self.client.force_login(self.manager)

        response = self.client.post(
            self.url,
            {"quantity_change": "-9", "note": "Damaged units"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "An adjustment cannot reduce stock below zero.")
        self.product.refresh_from_db()
        self.assertEqual(self.product.current_stock, 8)
        self.assertEqual(InventoryAdjustment.objects.count(), 0)

    def test_viewer_cannot_adjust_inventory(self):
        self.client.force_login(self.viewer)

        response = self.client.post(
            self.url,
            {"quantity_change": "1", "note": "Unauthorized"},
        )

        self.assertEqual(response.status_code, 403)
        self.product.refresh_from_db()
        self.assertEqual(self.product.current_stock, 8)

    def test_anonymous_user_is_redirected_to_login(self):
        response = Client().get(self.url)

        self.assertEqual(response.status_code, 302)
        self.assertIn("/accounts/login/", response.url)

    def test_product_detail_shows_adjustment_history(self):
        adjust_inventory(self.product.pk, 2, "Cycle count correction", self.manager)
        self.client.force_login(self.viewer)

        response = self.client.get(reverse("products:detail", args=[self.product.pk]))

        self.assertContains(response, "Recent stock adjustments")
        self.assertContains(response, "Cycle count correction")
        self.assertContains(response, "+2")
        self.assertNotContains(response, reverse("products:adjust_stock", args=[self.product.pk]))

    def test_product_detail_offers_adjustment_to_managers(self):
        self.client.force_login(self.manager)

        response = self.client.get(reverse("products:detail", args=[self.product.pk]))

        self.assertContains(response, reverse("products:adjust_stock", args=[self.product.pk]))


class InventoryAdjustmentAPITests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.manager = user_model.objects.create_user(
            username="api-stock-manager",
            password="test-password",
            role=user_model.Role.MANAGER,
        )
        self.viewer = user_model.objects.create_user(
            username="api-stock-viewer",
            password="test-password",
            role=user_model.Role.VIEWER,
        )
        self.product = Product.objects.create(
            sku="API-STOCK-1", name="API inventory item", current_stock=12
        )
        self.client = APIClient()
        self.url = reverse("product-stock-adjustments", args=[self.product.pk])

    def test_manager_can_adjust_stock_through_api(self):
        self.client.force_authenticate(user=self.manager)

        response = self.client.post(
            self.url,
            {"quantity_change": -2, "note": "Damaged units"},
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["stock_before"], 12)
        self.assertEqual(response.data["stock_after"], 10)
        self.assertEqual(response.data["created_by_username"], self.manager.username)
        self.product.refresh_from_db()
        self.assertEqual(self.product.current_stock, 10)

    def test_api_rejects_zero_and_below_zero_adjustments(self):
        self.client.force_authenticate(user=self.manager)

        for quantity_change in (0, -13):
            with self.subTest(quantity_change=quantity_change):
                response = self.client.post(
                    self.url,
                    {"quantity_change": quantity_change, "note": "Inventory correction"},
                    format="json",
                )
                self.assertEqual(response.status_code, 400)

        self.product.refresh_from_db()
        self.assertEqual(self.product.current_stock, 12)
        self.assertEqual(InventoryAdjustment.objects.count(), 0)

    def test_viewer_cannot_write_adjustments_through_api(self):
        self.client.force_authenticate(user=self.viewer)

        response = self.client.post(
            self.url,
            {"quantity_change": 1, "note": "Unauthorized"},
            format="json",
        )

        self.assertEqual(response.status_code, 403)
        self.product.refresh_from_db()
        self.assertEqual(self.product.current_stock, 12)

    def test_viewer_can_read_adjustment_history(self):
        adjust_inventory(self.product.pk, 4, "Received shipment", self.manager)
        self.client.force_authenticate(user=self.viewer)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["stock_before"], 12)
        self.assertEqual(response.data[0]["stock_after"], 16)
        self.assertEqual(response.data[0]["note"], "Received shipment")
