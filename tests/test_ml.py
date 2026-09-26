"""ML pipeline tests: feature engineering + prediction input validation."""
from datetime import date, timedelta

from django.test import TestCase

from apps.products.models import Product
from apps.sales.models import SalesRecord
from ml.preprocessing.features import build_training_frame, build_prediction_row, FEATURE_COLUMNS


class FeatureEngineeringTests(TestCase):
    def setUp(self):
        self.product = Product.objects.create(
            sku="ML-001", name="ML Test Product", current_stock=100,
            minimum_stock=20, maximum_stock=500, safety_stock=15,
            supplier_lead_time=5, unit_price="15.00",
        )
        today = date.today()
        for i in range(60):
            SalesRecord.objects.create(
                product=self.product, date=today - timedelta(days=i),
                quantity_sold=5 + (i % 7), unit_price="15.00",
            )

    def test_training_frame_has_expected_columns(self):
        qs = SalesRecord.objects.filter(product=self.product)
        df = build_training_frame(qs, self.product, horizon_days=7)
        self.assertIsNotNone(df)
        for col in FEATURE_COLUMNS:
            self.assertIn(col, df.columns)

    def test_no_leakage_columns_in_features(self):
        """The label column must never appear in the feature set."""
        self.assertNotIn("stockout_within_horizon", FEATURE_COLUMNS)

    def test_prediction_row_shape(self):
        qs = SalesRecord.objects.filter(product=self.product)
        row = build_prediction_row(qs, self.product)
        self.assertIsNotNone(row)
        self.assertEqual(len(row), 1)
        for col in FEATURE_COLUMNS:
            self.assertIn(col, row.columns)

    def test_insufficient_history_returns_none(self):
        sparse_product = Product.objects.create(
            sku="ML-002", name="Sparse Product", current_stock=10, supplier_lead_time=5,
        )
        qs = SalesRecord.objects.filter(product=sparse_product)
        df = build_training_frame(qs, sparse_product, horizon_days=7)
        self.assertIsNone(df)
