"""
Management command: python manage.py seed_data

Loads ml/data/sample_products.csv and ml/data/sample_sales.csv (generate
them first with `python ml/data/generate_sample_data.py` if they don't
exist) into the database via the normal Django ORM/import services, so the
app has realistic data to explore immediately after setup.
"""
import os
import pandas as pd
from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import transaction


class Command(BaseCommand):
    help = "Seed the database with the generated realistic sample dataset."

    def add_arguments(self, parser):
        parser.add_argument("--skip-sales", action="store_true",
                             help="Only load products/categories/suppliers, skip the (large) sales history import.")

    def handle(self, *args, **options):
        from apps.products.models import Category, Supplier, Warehouse, Product
        from apps.sales.models import SalesRecord

        data_dir = settings.BASE_DIR / "ml" / "data"
        products_path = data_dir / "sample_products.csv"
        sales_path = data_dir / "sample_sales.csv"

        if not products_path.exists():
            self.stderr.write(self.style.ERROR(
                "Sample data not found. Run: python ml/data/generate_sample_data.py"
            ))
            return

        products_df = pd.read_csv(products_path)
        created_products = 0
        sku_to_product = {}

        with transaction.atomic():
            for _, row in products_df.iterrows():
                category, _ = Category.objects.get_or_create(name=row["category"])
                supplier, _ = Supplier.objects.get_or_create(name=row["supplier"])
                warehouse, _ = Warehouse.objects.get_or_create(name=row["warehouse"])
                product, created = Product.objects.update_or_create(
                    sku=row["sku"],
                    defaults=dict(
                        name=row["name"], category=category, supplier=supplier, warehouse=warehouse,
                        current_stock=int(row["current_stock"]), minimum_stock=int(row["minimum_stock"]),
                        maximum_stock=int(row["maximum_stock"]), safety_stock=int(row["safety_stock"]),
                        supplier_lead_time=int(row["supplier_lead_time"]), unit_price=float(row["unit_price"]),
                    ),
                )
                sku_to_product[row["sku"]] = product
                created_products += created

        self.stdout.write(self.style.SUCCESS(
            f"Loaded {len(products_df)} products ({created_products} newly created)."
        ))

        if options["skip_sales"]:
            return

        if not sales_path.exists():
            self.stderr.write(self.style.WARNING("No sample sales CSV found; skipping sales import."))
            return

        sales_df = pd.read_csv(sales_path)
        sales_df["date"] = pd.to_datetime(sales_df["date"]).dt.date

        SalesRecord.objects.filter(product__sku__in=sku_to_product.keys()).delete()
        warehouse_cache = {}
        batch = []
        for _, row in sales_df.iterrows():
            wname = row.get("warehouse")
            if wname not in warehouse_cache:
                warehouse_cache[wname], _ = Warehouse.objects.get_or_create(name=wname)
            batch.append(SalesRecord(
                product=sku_to_product[row["product_id"]], date=row["date"],
                quantity_sold=int(row["quantity_sold"]), unit_price=float(row["unit_price"]),
                warehouse=warehouse_cache[wname],
            ))
            if len(batch) >= 5000:
                SalesRecord.objects.bulk_create(batch)
                batch = []
        if batch:
            SalesRecord.objects.bulk_create(batch)

        self.stdout.write(self.style.SUCCESS(f"Loaded {len(sales_df)} sales records."))
        self.stdout.write(self.style.SUCCESS(
            "Done. Next: python manage.py train_models"
        ))
