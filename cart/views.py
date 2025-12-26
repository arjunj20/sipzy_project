from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from .utils import get_user_cart,recalculate_cart_totals, revalidate_cart_prices
from django.http import JsonResponse
from .models import CartItems,Cart
from .utils import get_user_cart
from django.views.decorators.http import require_POST
from decimal import Decimal
from authenticate.models import Address
from orders.models import Order,OrderItem
from django.contrib import messages
from authenticate.models import Address
from django.views.decorators.cache import never_cache
from django.urls import reverse


@never_cache
def cart_page(request):
    if not request.user.is_authenticated or request.user.is_superuser:
        return redirect("user_login")

    cart = get_user_cart(request.user)

    revalidate_cart_prices(cart)

    recalculate_cart_totals(cart)

    context = {
        "cart": cart,
        "cart_items": cart.cart_items.all(),
        "sub_total": cart.item_subtotal,
        "tax": cart.tax,
        "shipping_fee": cart.shipping_fee,
        "total": cart.total_price,
        "breadcrumbs": [
            {"label": "Home", "url": "/"},
            {"label": "Cart", "url": ""}
        ]   
    }

    return render(request, "cart_page.html", context)

from decimal import Decimal
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.views.decorators.cache import never_cache
from offers.utils import get_best_offer_for_product, apply_offer
from products.models import ProductVariants

@never_cache
@require_POST
def update_cart_item(request):
    if not request.user.is_authenticated or request.user.is_superuser:
        return JsonResponse({"error": "Unauthorized"}, status=401)

    errors = {}

    item_id = request.POST.get("item_id")
    quantity = request.POST.get("quantity")
    variant_id = request.POST.get("variant_id")

    cart = get_user_cart(request.user)

    try:
        item = CartItems.objects.select_related(
            "variant", "variant__product"
        ).get(id=item_id, cart=cart)
    except CartItems.DoesNotExist:
        return JsonResponse({"error": "Item not found"}, status=404)

    # ---------------- Quantity ----------------
    try:
        quantity = int(quantity)
    except (TypeError, ValueError):
        quantity = 1

    quantity = max(quantity, 1)

    # ---------------- Variant change ----------------
    if variant_id:
        # IMPORTANT: reload variant object
        item.variant = ProductVariants.objects.get(id=variant_id)

        # Recalculate unit price for new variant
        offer = get_best_offer_for_product(item.variant.product)
        item.unit_price = (
            apply_offer(item.variant.price, offer)
            if offer else item.variant.price
        )

    # ---------------- Stock limit ----------------
    max_limit = min(item.variant.stock, 5)
    if quantity > max_limit:
        quantity = max_limit
        errors["quantity"] = f"Only {max_limit} units available."

    item.quantity = quantity

    # ---------------- Tax (on unit_price) ----------------
    gst_rate = Decimal(str(getattr(item.variant, "gst_rate", 18)))
    unit_tax = (item.unit_price * gst_rate / Decimal("100")).quantize(
        Decimal("0.01")
    )

    item.tax_amount = unit_tax * quantity
    item.total_price = (item.unit_price * quantity) + item.tax_amount

    item.save()

    # ---------------- Cart totals ----------------
    recalculate_cart_totals(cart)

    

    return JsonResponse({
        "success": True,
        "unit_price": str(item.unit_price),
        "item_total": str(item.total_price),
        "subtotal": str(cart.item_subtotal),
        "shipping": str(cart.shipping_fee),
        "tax": str(cart.tax),
        "total": str(cart.total_price),
        "corrected_quantity": quantity,
        "errors": errors,
    })



@never_cache
@require_POST
def ajax_delete_item(request):

    if not request.user.is_authenticated or request.user.is_superuser:
        return redirect("landing_page")
    item_id = request.POST.get("id")

    cart = get_user_cart(request.user)
    item = get_object_or_404(CartItems, id=item_id, cart=cart)
    item.delete()
    cart_items = cart.cart_items.all()
    cart.item_subtotal = sum(i.total_price for i in cart_items)
    cart.total_price = cart.item_subtotal + cart.shipping_fee
    cart.save()
    recalculate_cart_totals(cart)
    return JsonResponse({
        "success": True,
        "subtotal": float(cart.item_subtotal),
        "total": float(cart.total_price),    
        "shipping": float(cart.shipping_fee),
        "tax": float(cart.tax),   
        "remaining_items": cart_items.count(),
    })


@never_cache
def checkout_page(request):

    if not request.user.is_authenticated or request.user.is_superuser:
        return redirect("user_login")
    address=Address.objects.filter(user=request.user)

    cart = Cart.objects.get(user=request.user)
    cart_items = CartItems.objects.filter(cart=cart)
    subtotal = sum(i.total_price for i in cart_items)
    shipping_fee = 50 if subtotal<1000 else 0
    total_price = subtotal + shipping_fee 
    context = {
        "addresses": address,
        "cart_items": cart_items,
        "subtotal": subtotal,
        "shipping_fee": shipping_fee,
        "total_price": total_price,
        "breadcrumbs": [
            {"label": "Home", "url": "/"},
            {"label": "Cart", "url": reverse("cart_page")},
            {"label": "Checkout", "url": ""}
        ]
    }
    return render(request, "checkout.html" , context)

@never_cache
def place_order(request):

    if not request.user.is_authenticated or request.user.is_superuser:
        return redirect("user_login")

    if request.method == 'POST':
        user = request.user
        selected_address_id = request.POST.get("selected_address")
        payment_method = request.POST.get("payment_method")

        if not selected_address_id:
            messages.error(request, "Please select a delivery address")
            return redirect("checkout_page")

        try:
            address = Address.objects.get(id=selected_address_id, user=user)
        except Address.DoesNotExist:
            messages.error(request, "Invalid address selected")
            return redirect("checkout_page")

        cart_items = CartItems.objects.filter(cart__user=user)

        subtotal = sum(item.total_price for item in cart_items)
        shipping_fee = 50 if subtotal < 1000 else 0

        tax = Decimal("0")
        for item in cart_items:
            gst_rate = Decimal(item.variant.gst_rate)
            item_tax_amount = item.total_price * (gst_rate / Decimal("100"))
            tax += item_tax_amount

        tax = round(tax, 2)
        discount = Decimal("0")
        total_price = subtotal + shipping_fee + tax - discount

        order = Order.objects.create(
            user=user,
            address=address,
            payment_method=payment_method,
            subtotal=subtotal,
            tax=tax,
            shipping_fee=shipping_fee,
            discount=discount,
            total=total_price,
            payment_status="not paid" if payment_method == "COD" else "pending",
        )

        count = 1
        for i in cart_items:
            order_item = OrderItem.objects.create(
                order=order,
                product=i.variant.product,
                variant=i.variant,
                quantity=i.quantity,
                price=i.total_price,
            )

            order_item.sub_order_id = f"{order.order_number}-{count}"
            order_item.save(update_fields=["sub_order_id"])
            variant = i.variant
            variant.stock -= i.quantity
            variant.save(update_fields=["stock"])

            count += 1

        cart_items.delete()

        return redirect("order_placed", order_id=order.id)


    return redirect("checkout_page")

@never_cache
def order_placed(request, order_id):
    if not request.user.is_authenticated or request.user.is_superuser:
        return redirect("landing_page")
    order = Order.objects.get(id=order_id, user=request.user)
    return render(request, "order_placed.html", {"order": order})


@never_cache
def add_address(request):
    if not request.user.is_authenticated or request.user.is_superuser:
        return redirect("landing_page")
    if request.method == "POST":
        Address.objects.create(
            user=request.user,
            full_name=request.POST.get("full_name"),
            phone_number=request.POST.get("phone_number"),
            address_line1=request.POST.get("address_line1"),
            address_line2=request.POST.get("address_line2"),
            city=request.POST.get("city"),
            state=request.POST.get("state"),
            country="India",
            pincode=request.POST.get("pincode"),
        )

        messages.success(request, "Address added successfully.")
        return redirect("checkout_page")  

    return render(request, "add_address.html")

@never_cache
def edit_address(request, uuid):

    if not request.user.is_authenticated or request.user.is_superuser:
        return redirect("landing_page")
    
    address = get_object_or_404(Address, uuid=uuid, user=request.user)

    if request.method == "POST":
        address.full_name = request.POST.get("full_name")
        address.phone_number = request.POST.get("phone_number")
        address.address_line1 = request.POST.get("address_line1")
        address.address_line2 = request.POST.get("address_line2")
        address.city = request.POST.get("city")
        address.state = request.POST.get("state")
        address.pincode = request.POST.get("pincode")
        address.save()

        messages.success(request, "Address updated successfully.")
        return redirect("checkout_page")

    return render(request, "edit_address.html", {"address": address})
