from cart.models import Cart, CartItems
from wishlist.models import Wishlist

def counter_processor(request):
    cart_count = 0
    wishlist_count = 0

    if request.user.is_authenticated:
        # 1. Fix Cart Count (This looks correct assuming your CartItems model is set up right)
        # Note: Ensure you import CartItems correctly
        cart_count = CartItems.objects.filter(cart__user=request.user).count()

        wishlist_count = Wishlist.objects.filter(user=request.user).count()

    return {
        'cart_count': cart_count,
        'wishlist_count': wishlist_count,
    }