"""
Sales CSV validation and import.

Expected columns (header row required):
    date, product_id, quantity_sold, unit_price[, warehouse]

`product_id` may be either the numeric Product PK or the Product SKU.
"""
import csv
import io
from datetime import datetime
from decimal import Decimal, InvalidOperation

from django.db import transaction
from django.utils import timezone

from apps.products.models import Product, Warehouse
from .models import SalesRecord, SalesImportLog

REQUIRED_COLUMNS = {"date", "product_id", "quantity_sold", "unit_price"}


def _parse_date(value):
    value = value.strip()
    for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%d-%m-%Y"):
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            continue
    raise ValueError(f"Unrecognized date format: {value}")


def _resolve_product(raw_id, cache):
    raw_id = raw_id.strip()
    if raw_id in cache:
        return cache[raw_id]
    product = None
    if raw_id.isdigit():
        product = Product.objects.filter(pk=int(raw_id)).first()
    if product is None:
        product = Product.objects.filter(sku=raw_id).first()
    if product is None:
        raise ValueError(f"Unknown product_id/SKU: {raw_id}")
    cache[raw_id] = product
    return product


def validate_and_import_csv(file_obj, uploaded_by=None, file_name="upload.csv"):
    """Validate an uploaded CSV file and bulk-create SalesRecord rows.

    Returns the created SalesImportLog instance.
    """
    raw = file_obj.read()
    decoded = io.StringIO(raw.decode("utf-8-sig"))
    reader = csv.DictReader(decoded)

    if not reader.fieldnames:
        raise ValueError("CSV must include a header row.")
    headers = [column.strip().lower() for column in reader.fieldnames]
    if len(headers) != len(set(headers)):
        raise ValueError("CSV contains duplicate column names.")
    if not REQUIRED_COLUMNS.issubset(set(headers)):
        missing = REQUIRED_COLUMNS - set(headers)
        raise ValueError(f"CSV is missing required column(s): {', '.join(sorted(missing))}")
    reader.fieldnames = headers

    product_cache, warehouse_cache = {}, {}
    to_create, errors, processed = [], [], 0

    for i, row in enumerate(reader, start=2):  # header is row 1
        processed += 1
        try:
            if not row.get("date") or not row.get("product_id"):
                raise ValueError("Missing date or product_id")
            date = _parse_date(row["date"])
            if date > timezone.localdate():
                raise ValueError("date cannot be in the future")
            product = _resolve_product(row["product_id"], product_cache)
            quantity = Decimal(row["quantity_sold"])
            if not quantity.is_finite() or quantity != quantity.to_integral_value():
                raise ValueError("quantity_sold must be a whole number")
            qty = int(quantity)
            if qty < 0:
                raise ValueError("quantity_sold cannot be negative")
            price = Decimal(row["unit_price"])
            if not price.is_finite() or price < 0:
                raise ValueError("unit_price must be a finite, non-negative amount")

            warehouse = None
            wname = (row.get("warehouse") or "").strip()
            if wname:
                if wname not in warehouse_cache:
                    warehouse_cache[wname], _ = Warehouse.objects.get_or_create(name=wname)
                warehouse = warehouse_cache[wname]

            to_create.append(SalesRecord(
                product=product, date=date, quantity_sold=qty, unit_price=price, warehouse=warehouse,
            ))
        except (InvalidOperation, KeyError, TypeError, ValueError) as e:
            errors.append(f"Row {i}: {e}")

    with transaction.atomic():
        created = SalesRecord.objects.bulk_create(to_create, batch_size=1000)

    log = SalesImportLog.objects.create(
        file_name=file_name,
        rows_processed=processed,
        rows_created=len(created),
        rows_failed=len(errors),
        errors="\n".join(errors[:200]),
        uploaded_by=uploaded_by,
    )
    return log
