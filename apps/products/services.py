from django.db import transaction

from .models import InventoryAdjustment, Product


MAX_STOCK = 2_147_483_647


@transaction.atomic
def adjust_inventory(product_id, quantity_change, note, user):
    if type(quantity_change) is not int:
        raise ValueError("Quantity change must be a whole number.")
    if quantity_change == 0:
        raise ValueError("Quantity change cannot be zero.")
    if not isinstance(note, str) or not note.strip():
        raise ValueError("A note is required for every inventory adjustment.")
    note = note.strip()
    if len(note) > 500:
        raise ValueError("The adjustment note cannot exceed 500 characters.")

    product = Product.objects.select_for_update().get(pk=product_id, is_active=True)
    stock_before = product.current_stock
    stock_after = stock_before + quantity_change
    if stock_after < 0:
        raise ValueError("An adjustment cannot reduce stock below zero.")
    if stock_after > MAX_STOCK:
        raise ValueError("The adjusted stock exceeds the supported limit.")

    product.current_stock = stock_after
    product.save(update_fields=["current_stock", "updated_at"])
    return InventoryAdjustment.objects.create(
        product=product,
        quantity_change=quantity_change,
        stock_before=stock_before,
        stock_after=stock_after,
        note=note,
        created_by=user,
    )
