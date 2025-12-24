from .models import Cart
from decimal import Decimal
from offers.utils import get_best_offer_for_product, apply_offer


def get_user_cart(user):
    cart, created = Cart.objects.get_or_create(user=user)
    return cart


from decimal import Decimal


def recalculate_cart_totals(cart):
    items = cart.cart_items.filter(
        variant__product__is_active=True
    )

    cart.item_subtotal = sum(
        (item.unit_price * item.quantity)
        for item in items
    )

    cart.tax = sum(
        (item.tax_amount or Decimal("0.00"))
        for item in items
    )

    cart.shipping_fee = (
        Decimal("50.00")
        if cart.item_subtotal < Decimal("1000.00") and cart.item_subtotal > 0
        else Decimal("0.00")
    )

    cart.total_price = (
        cart.item_subtotal +
        cart.tax +
        cart.shipping_fee
    )

    cart.save()


def revalidate_cart_prices(cart):
    for item in cart.cart_items.select_related("variant", "variant__product"):
        offer = get_best_offer_for_product(item.variant.product)

        new_unit_price = (
            apply_offer(item.variant.price, offer)
            if offer else item.variant.price
        )

        if new_unit_price != item.unit_price:
            gst_rate = getattr(item.variant, "gst_rate", 18)
            unit_tax = (new_unit_price * Decimal(gst_rate) / 100).quantize(Decimal("0.01"))

            item.unit_price = new_unit_price
            item.tax_amount = unit_tax * item.quantity
            item.total_price = (new_unit_price * item.quantity) + item.tax_amount
            item.save()


