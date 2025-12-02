from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from .utils import get_user_cart


def cart_page(request):

    if not request.user.is_authenticated and request.user.is_superuser:
        return redirect("user_login")
    cart = get_user_cart(request.user)
    items = cart.cart_items.select_related("variant", "variant__product")

    context = {
        "cart": cart,
        "cart_items": items,
        "sub_total": cart.item_subtotal,
        "shipping_fee": cart.shipping_fee,
        "total": cart.total_price,

    }
    return render(request, "cart_page.html", context)

from django.http import JsonResponse
from .models import CartItems
from .utils import get_user_cart
from django.views.decorators.http import require_POST

@require_POST
def update_cart_item(request):
    errors = {}
    item_id = request.POST.get("item_id")
    quantity = request.POST.get("quantity")
    variant_id = request.POST.get("variant_id")

    cart = get_user_cart(request.user)

    try:
        item = CartItems.objects.get(id=item_id, cart=cart)
    except CartItems.DoesNotExist:
        return JsonResponse({"error": "Item not found"}, status=404)

    # --- Convert quantity safely ---
    try:
        quantity = int(quantity)
    except:
        quantity = 1  # default fallback

    # --- Quantity must be at least 1 ---
    if quantity < 1:
        quantity = 1

    # --- Update Variant ---
    if variant_id:
        item.variant_id = variant_id

    # --- Limit based on stock and max allowed ---
    max_limit = min(item.variant.stock, 5)

    if quantity > max_limit:
        quantity = max_limit
        errors["quantity"] = f"Oops! You’ve reached the limit. Only {max_limit} units are allowed."

    # --- Apply update ---
    item.quantity = quantity
    item.total_price = item.variant.price * quantity
    item.save()

    # --- Recalculate cart totals ---
    cart_items = cart.cart_items.all()
    cart.item_subtotal = sum(i.total_price for i in cart_items)
    cart.total_price = cart.item_subtotal + cart.shipping_fee
    cart.save()

    return JsonResponse({
        "success": True,
        "item_total": float(item.total_price),
        "unit_price": float(item.variant.price),
        "subtotal": float(cart.item_subtotal),
        "shipping": float(cart.shipping_fee),
        "total": float(cart.total_price),
        "corrected_quantity": quantity,
        "errors": errors,
    })


@require_POST
def ajax_delete_item(request):
    item_id = request.POST.get("id")

    cart = get_user_cart(request.user)
    item = get_object_or_404(CartItems, id=item_id, cart=cart)
    item.delete()

    # Recalculate totals
    cart_items = cart.cart_items.all()
    cart.item_subtotal = sum(i.total_price for i in cart_items)
    cart.total_price = cart.item_subtotal + cart.shipping_fee
    cart.save()

    return JsonResponse({
        "success": True,
        "subtotal": float(cart.item_subtotal),
        "total": float(cart.total_price),
        "remaining_items": cart_items.count(),
    })

