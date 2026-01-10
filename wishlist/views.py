from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from products.models import Products
from .models import Wishlist
from django.db.models import Min
from django.db import transaction
from decimal import Decimal

from cart.models import Cart, CartItems
from django.views.decorators.http import require_POST


@login_required
def add_to_wishlist(request, product_uuid):
    if request.method == "POST":
        product = get_object_or_404(Products, uuid=product_uuid)

        Wishlist.objects.get_or_create(
            user=request.user,
            product=product
        )

    return redirect(request.META.get("HTTP_REFERER", "home"))


@login_required
@require_POST
def remove_from_wishlist(request, product_uuid):
    Wishlist.objects.filter(
        user=request.user,
        uuid=product_uuid
    ).delete()

    return JsonResponse({"status": "success", "message": "Removed from wishlist"})


@login_required
@transaction.atomic
def move_to_cart(request, product_uuid):
    product = get_object_or_404(Products, uuid=product_uuid)

    # ✅ get cheapest variant (same logic as product list)
    variant = product.variants.order_by("price").first()

    if not variant:
        return redirect("wishlist")  # no stock / no variants

    cart, _ = Cart.objects.get_or_create(user=request.user)

    cart_item, created = CartItems.objects.get_or_create(
        cart=cart,
        variant=variant,   # ✅ CORRECT
        defaults={
            "quantity": 1,
            "unit_price": variant.price,
            "total_price": variant.price,
            "tax_amount": Decimal("0.00"),
        }
    )

    if not created:
        cart_item.quantity += 1
        cart_item.total_price = cart_item.quantity * cart_item.unit_price
        cart_item.save()

    # ✅ remove from wishlist
    Wishlist.objects.filter(
        user=request.user,
        product=product
    ).delete()

    return redirect("wishlist")

login_required
def wishlist_page(request):

    if not request.user.is_authenticated or request.user.is_superuser:
        return redirect("user_login")
    wishlist_items = (
        Wishlist.objects
        .filter(user=request.user)
        .select_related("product")
        .prefetch_related("product__variants")
    )

    for item in wishlist_items:
        variants = item.product.variants.all()
        item.default_variant = min(variants, key=lambda v: v.price, default=None)

    return render(request, "wishlist/wishlist.html", {
        "wishlist_items": wishlist_items
    })


