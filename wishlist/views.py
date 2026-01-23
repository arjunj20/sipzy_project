from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from products.models import Products
from .models import Wishlist
from django.db.models import Min
from django.db import transaction
from decimal import Decimal
from django.contrib import messages
from cart.models import Cart, CartItems
from django.views.decorators.http import require_POST
from offers.utils import get_best_offer_for_product, apply_offer


@login_required
def add_to_wishlist(request, product_uuid):
    if request.method == "POST":
        product = get_object_or_404(Products, uuid=product_uuid)

        Wishlist.objects.get_or_create(
            user=request.user,
            product=product
        )
        messages.success(request, "the item has added in the wishlist")
    return redirect(request.META.get("HTTP_REFERER", "home"))


@login_required
@require_POST
def remove_from_wishlist(request, product_uuid):
    deleted, _ = Wishlist.objects.filter(
        user=request.user,
        product__uuid=product_uuid  
    ).delete()

    if deleted == 0:
        return JsonResponse({
            "status": "error",
            "message": "Item not found in wishlist"
        }, status=404)

    return JsonResponse({
        "status": "success",
        "message": "Removed from wishlist"
    })



@login_required
@transaction.atomic
def move_to_cart(request, product_uuid):
    product = get_object_or_404(Products, uuid=product_uuid)

    variant = product.variants.order_by("price").first()

    if not variant:
        return redirect("wishlist")  

    cart, _ = Cart.objects.get_or_create(user=request.user)

    cart_item, created = CartItems.objects.get_or_create(
        cart=cart,
        variant=variant,  
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
        product = item.product
        variants = item.product.variants.all()
        item.default_variant = min(variants, key=lambda v: v.price, default=None)
        for i in variants:
            i.offer_price = None
            offer = get_best_offer_for_product(product)

            if offer:
                i.offer_price = apply_offer(i.price, offer)
                i.applied_offer = offer

    

    return render(request, "wishlist/wishlist.html", {
        "wishlist_items": wishlist_items
    })


