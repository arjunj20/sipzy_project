from .models import Cart


def get_user_cart(user):
    cart, created = Cart.objects.get_or_create(user=user)
    return cart


def recalculate_cart_totals(cart):
    items = cart.cart_items.all()

    cart.item_subtotal = sum(item.total_price for item in items)
    cart.shipping_fee = 50 if cart.item_subtotal < 1000 else 0
    cart.total_price = cart.item_subtotal + cart.shipping_fee

    cart.save()
