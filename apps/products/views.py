import csv
import io
from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import HttpResponse
from django.shortcuts import render, redirect, get_object_or_404

from apps.accounts.permissions import role_required
from apps.accounts.models import User
from .forms import ProductForm
from .models import Product, Category, Supplier, Warehouse, STOCK_STATUS_LABELS


def _parse_non_negative_integer(value, field_name, default):
    raw = str(value or "").strip()
    if not raw:
        return default
    try:
        parsed = Decimal(raw)
    except InvalidOperation as exc:
        raise ValueError(f"{field_name} must be a whole number.") from exc
    if not parsed.is_finite() or parsed < 0 or parsed != parsed.to_integral_value():
        raise ValueError(f"{field_name} must be a non-negative whole number.")
    return int(parsed)


def _parse_unit_price(value):
    raw = str(value or "0").strip()
    try:
        price = Decimal(raw)
    except InvalidOperation as exc:
        raise ValueError("unit_price must be a finite, non-negative amount.") from exc
    if not price.is_finite() or price < 0:
        raise ValueError("unit_price must be a finite, non-negative amount.")
    if price >= Decimal("100000000"):
        raise ValueError("unit_price cannot exceed 99999999.99.")
    try:
        if price != price.quantize(Decimal("0.01")):
            raise ValueError("unit_price cannot have more than two decimal places.")
    except InvalidOperation as exc:
        raise ValueError("unit_price must fit within 10 digits.") from exc
    return price


@login_required
def product_list(request):
    qs = Product.objects.select_related("category", "supplier", "warehouse").filter(is_active=True)

    q = request.GET.get("q", "").strip()
    if q:
        qs = qs.filter(Q(name__icontains=q) | Q(sku__icontains=q) |
                        Q(category__name__icontains=q) | Q(supplier__name__icontains=q))

    category = request.GET.get("category")
    if category:
        qs = qs.filter(category_id=category)

    warehouse = request.GET.get("warehouse")
    if warehouse:
        qs = qs.filter(warehouse_id=warehouse)

    status = request.GET.get("status")
    products = list(qs)
    if status:
        products = [p for p in products if p.stock_status == status]

    paginator = Paginator(products, 25)
    page_obj = paginator.get_page(request.GET.get("page"))

    context = {
        "page_obj": page_obj,
        "categories": Category.objects.all(),
        "warehouses": Warehouse.objects.all(),
        "status_labels": STOCK_STATUS_LABELS,
        "q": q,
    }
    return render(request, "products/list.html", context)


@login_required
def product_detail(request, pk):
    product = get_object_or_404(Product, pk=pk)
    from apps.predictions.services import get_latest_risk
    from apps.forecasting.services import get_latest_forecast
    from apps.recommendations.services import build_recommendation

    context = {
        "product": product,
        "risk": get_latest_risk(product),
        "forecast": get_latest_forecast(product, horizon=7),
        "forecast_30": get_latest_forecast(product, horizon=30),
        "recommendation": build_recommendation(product),
    }
    return render(request, "products/detail.html", context)


@login_required
@role_required(User.Role.ADMIN, User.Role.MANAGER)
def product_create(request):
    form = ProductForm(request.POST or None)
    if request.method == "POST":
        if form.is_valid():
            product = form.save()
            messages.success(request, f"Product {product.sku} created.")
            return redirect("products:detail", pk=product.pk)
    return render(request, "products/form.html", {"form": form})


@login_required
@role_required(User.Role.ADMIN, User.Role.MANAGER)
def product_edit(request, pk):
    product = get_object_or_404(Product, pk=pk)
    form = ProductForm(request.POST or None, instance=product)
    if request.method == "POST":
        if form.is_valid():
            product = form.save()
            messages.success(request, f"Product {product.sku} updated.")
            return redirect("products:detail", pk=product.pk)
    return render(request, "products/form.html", {"form": form, "product": product})


@login_required
@role_required(User.Role.ADMIN, User.Role.MANAGER)
def product_delete(request, pk):
    product = get_object_or_404(Product, pk=pk)
    if request.method == "POST":
        product.is_active = False
        product.save(update_fields=["is_active"])
        messages.success(request, f"Product {product.sku} deleted.")
        return redirect("products:list")
    return render(request, "products/confirm_delete.html", {"product": product})


@login_required
@role_required(User.Role.ADMIN, User.Role.MANAGER)
def product_import(request):
    """Bulk import products from CSV: sku,name,category,supplier,warehouse,
    current_stock,minimum_stock,maximum_stock,safety_stock,supplier_lead_time,unit_price"""
    if request.method == "POST" and request.FILES.get("file"):
        f = request.FILES["file"]
        decoded = io.StringIO(f.read().decode("utf-8-sig"))
        reader = csv.DictReader(decoded)
        required = {"sku", "name"}
        if not reader.fieldnames:
            messages.error(request, "CSV must include a header row.")
            return redirect("products:import")
        headers = [column.strip().lower() for column in reader.fieldnames]
        if len(headers) != len(set(headers)):
            messages.error(request, "CSV contains duplicate column names.")
            return redirect("products:import")
        if not required.issubset(set(headers)):
            messages.error(request, f"CSV must include columns: {', '.join(required)}")
            return redirect("products:import")
        reader.fieldnames = headers

        created, updated, errors = 0, 0, []
        for i, row in enumerate(reader, start=2):
            try:
                unit_price = _parse_unit_price(row.get("unit_price"))
                current_stock = _parse_non_negative_integer(row.get("current_stock"), "current_stock", 0)
                minimum_stock = _parse_non_negative_integer(row.get("minimum_stock"), "minimum_stock", 10)
                maximum_stock = _parse_non_negative_integer(row.get("maximum_stock"), "maximum_stock", 500)
                safety_stock = _parse_non_negative_integer(row.get("safety_stock"), "safety_stock", 20)
                supplier_lead_time = _parse_non_negative_integer(
                    row.get("supplier_lead_time"), "supplier_lead_time", 5
                )
                if maximum_stock < minimum_stock:
                    raise ValueError("maximum_stock cannot be less than minimum_stock.")
                category, _ = Category.objects.get_or_create(name=row.get("category", "General").strip() or "General")
                supplier = None
                if row.get("supplier"):
                    supplier, _ = Supplier.objects.get_or_create(name=row["supplier"].strip())
                warehouse = None
                if row.get("warehouse"):
                    warehouse, _ = Warehouse.objects.get_or_create(name=row["warehouse"].strip())

                obj, was_created = Product.objects.update_or_create(
                    sku=row["sku"].strip(),
                    defaults=dict(
                        name=row["name"].strip(),
                        category=category, supplier=supplier, warehouse=warehouse,
                        current_stock=current_stock,
                        minimum_stock=minimum_stock,
                        maximum_stock=maximum_stock,
                        safety_stock=safety_stock,
                        supplier_lead_time=supplier_lead_time,
                        unit_price=unit_price,
                    ),
                )
                created += was_created
                updated += not was_created
            except Exception as e:
                errors.append(f"Row {i}: {e}")

        messages.success(request, f"Import complete: {created} created, {updated} updated.")
        if errors:
            messages.warning(request, f"{len(errors)} row(s) had errors: " + "; ".join(errors[:5]))
        return redirect("products:list")

    return render(request, "products/import.html")


@login_required
def product_export(request):
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="products_export.csv"'
    writer = csv.writer(response)
    writer.writerow(["sku", "name", "category", "supplier", "warehouse", "current_stock",
                      "minimum_stock", "maximum_stock", "safety_stock", "supplier_lead_time",
                      "unit_price", "stock_status"])
    for p in Product.objects.select_related("category", "supplier", "warehouse").filter(is_active=True):
        writer.writerow([p.sku, p.name, p.category.name if p.category else "",
                          p.supplier.name if p.supplier else "", p.warehouse.name if p.warehouse else "",
                          p.current_stock, p.minimum_stock, p.maximum_stock, p.safety_stock,
                          p.supplier_lead_time, p.unit_price, p.stock_status])
    return response
