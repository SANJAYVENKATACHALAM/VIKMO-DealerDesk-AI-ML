import uuid
from decimal import Decimal

from django.db import transaction

from core.models import Product, Dealer, Order, OrderItem


def search_parts(query, category=None, brand=None, limit=10):
    """
    Search parts/products from the live database.

    Uses token-based searching so queries like:
        "brake pads"
        "brake"
        "royal enfield brake"
    can find matching products.
    """

    queryset = Product.objects.all()

    if query:
        words = [
            word.strip().lower()
            for word in query.split()
            if word.strip()
        ]

        for word in words:
            # Handle simple plural words.
            search_words = [word]

            if word.endswith("s") and len(word) > 3:
                search_words.append(word[:-1])

            word_query = None

            for search_word in search_words:
                current_query = (
                    Product.objects.filter(name__icontains=search_word)
                    | Product.objects.filter(
                        sku__icontains=search_word
                    )
                    | Product.objects.filter(
                        description__icontains=search_word
                    )
                    | Product.objects.filter(
                        vehicle_fitment__icontains=search_word
                    )
                )

                if word_query is None:
                    word_query = current_query
                else:
                    word_query = word_query | current_query

            queryset = queryset.filter(
                pk__in=word_query.values("pk")
            )

    if category:
        queryset = queryset.filter(category__iexact=category)

    if brand:
        queryset = queryset.filter(brand__iexact=brand)

    queryset = (
        queryset
        .select_related("inventory")
        .order_by("sku")[:limit]
    )

    results = []

    for product in queryset:
        results.append(
            {
                "sku": product.sku,
                "name": product.name,
                "category": product.category,
                "brand": product.brand,
                "vehicle_fitment": product.vehicle_fitment,
                "price": float(product.price),
                "stock": product.inventory.quantity,
                "description": product.description,
            }
        )

    return results


def check_stock(sku):
    """
    Check current stock for a specific SKU.
    """

    from core.models import Inventory

    try:
        inventory = (
            Inventory.objects
            .select_related("product")
            .get(product__sku=sku)
        )

    except Inventory.DoesNotExist:
        return {
            "found": False,
            "sku": sku,
            "message": f"SKU {sku} was not found.",
        }

    return {
        "found": True,
        "sku": inventory.product.sku,
        "name": inventory.product.name,
        "stock": inventory.quantity,
        "price": float(inventory.product.price),
    }


def create_draft_order(dealer_id, items):
    """
    Create a DRAFT order only.

    This function:
    - validates the dealer
    - validates SKUs
    - validates quantities
    - checks available stock
    - calculates totals
    - creates the order
    - creates order items
    - never decreases inventory
    - never confirms the order
    """

    if not items:
        return {
            "success": False,
            "error": "ITEMS_REQUIRED",
            "message": "At least one item is required.",
        }

    # ---------------------------------------------------------
    # Validate dealer
    # ---------------------------------------------------------

    try:
        dealer = Dealer.objects.get(id=dealer_id)

    except Dealer.DoesNotExist:
        return {
            "success": False,
            "error": "DEALER_NOT_FOUND",
            "message": f"Dealer with id {dealer_id} was not found.",
        }

    # ---------------------------------------------------------
    # Validate duplicate SKUs
    # ---------------------------------------------------------

    sku_list = []

    for item in items:
        sku = str(item.get("sku", "")).strip()

        if not sku:
            return {
                "success": False,
                "error": "SKU_REQUIRED",
                "message": "Every order item must contain a SKU.",
            }

        if sku in sku_list:
            return {
                "success": False,
                "error": "DUPLICATE_SKU",
                "message": f"SKU {sku} appears more than once.",
            }

        sku_list.append(sku)

    # ---------------------------------------------------------
    # Validate products and quantities
    # ---------------------------------------------------------

    validated_items = []

    for item in items:

        sku = str(item.get("sku", "")).strip()
        quantity = item.get("quantity")

        # Quantity must be an integer
        if isinstance(quantity, bool):
            return {
                "success": False,
                "error": "INVALID_QUANTITY",
                "message": f"Invalid quantity for SKU {sku}.",
            }

        try:
            quantity = int(quantity)

        except (TypeError, ValueError):
            return {
                "success": False,
                "error": "INVALID_QUANTITY",
                "message": f"Invalid quantity for SKU {sku}.",
            }

        if quantity <= 0:
            return {
                "success": False,
                "error": "INVALID_QUANTITY",
                "message": f"Quantity for SKU {sku} must be greater than 0.",
            }

        # -----------------------------------------------------
        # Find product
        # -----------------------------------------------------

        try:
            product = Product.objects.select_related("inventory").get(
                sku=sku
            )

        except Product.DoesNotExist:
            return {
                "success": False,
                "error": "PRODUCT_NOT_FOUND",
                "message": f"SKU {sku} was not found.",
            }

        # -----------------------------------------------------
        # Check inventory
        # -----------------------------------------------------

        available_stock = product.inventory.quantity

        if quantity > available_stock:
            return {
                "success": False,
                "error": "INSUFFICIENT_STOCK",
                "message": (
                    f"Insufficient stock for {sku}. "
                    f"Requested {quantity}, available {available_stock}."
                ),
                "sku": sku,
                "requested": quantity,
                "available": available_stock,
            }

        validated_items.append(
            {
                "product": product,
                "quantity": quantity,
                "unit_price": product.price,
            }
        )

    # ---------------------------------------------------------
    # Create draft order atomically
    # ---------------------------------------------------------

    with transaction.atomic():

        order_number = f"DRAFT-{uuid.uuid4().hex[:12].upper()}"

        order = Order.objects.create(
            order_number=order_number,
            dealer=dealer,
            status=Order.Status.DRAFT,
            subtotal=Decimal("0.00"),
            tax_total=Decimal("0.00"),
            grand_total=Decimal("0.00"),
        )

        subtotal = Decimal("0.00")

        created_items = []

        for item in validated_items:

            product = item["product"]
            quantity = item["quantity"]
            unit_price = item["unit_price"]

            line_subtotal = unit_price * quantity
            line_tax = Decimal("0.00")
            line_total = line_subtotal + line_tax

            OrderItem.objects.create(
                order=order,
                product=product,
                quantity=quantity,
                unit_price=unit_price,
                line_subtotal=line_subtotal,
                line_tax=line_tax,
                line_total=line_total,
            )

            subtotal += line_subtotal

            created_items.append(
                {
                    "sku": product.sku,
                    "name": product.name,
                    "quantity": quantity,
                    "unit_price": float(unit_price),
                    "line_subtotal": float(line_subtotal),
                    "line_tax": float(line_tax),
                    "line_total": float(line_total),
                }
            )

        tax_total = Decimal("0.00")
        grand_total = subtotal + tax_total

        order.subtotal = subtotal
        order.tax_total = tax_total
        order.grand_total = grand_total

        order.save(
            update_fields=[
                "subtotal",
                "tax_total",
                "grand_total",
                "updated_at",
            ]
        )

    # ---------------------------------------------------------
    # Return result
    # ---------------------------------------------------------

    return {
        "success": True,
        "message": "Draft order created successfully.",
        "order_number": order.order_number,
        "status": order.status,
        "dealer": {
            "id": dealer.id,
            "dealer_code": dealer.dealer_code,
            "name": dealer.name,
        },
        "items": created_items,
        "subtotal": float(subtotal),
        "tax_total": float(tax_total),
        "grand_total": float(grand_total),
    }