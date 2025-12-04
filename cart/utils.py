from .models import Cart
from decimal import Decimal


def get_user_cart(user):
    cart, created = Cart.objects.get_or_create(user=user)
    return cart


from decimal import Decimal

def recalculate_cart_totals(cart):
    items = cart.cart_items.filter(variant__product__is_active=True)

    cart.item_subtotal = sum(
        Decimal(str(item.variant.price)) * item.quantity
        for item in items
    )

    cart.tax = sum(
        Decimal(str(item.tax_amount))
        for item in items
    )
    cart.shipping_fee = Decimal('50.00') if cart.item_subtotal < Decimal('1000.00') and cart.item_subtotal > 0 else Decimal('0.00')

    cart.total_price = cart.item_subtotal + cart.tax + cart.shipping_fee

    cart.save()

