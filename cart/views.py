from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from .utils import get_user_cart,recalculate_cart_totals, revalidate_cart_prices
from django.http import JsonResponse
from .models import CartItems,Cart
from .utils import get_user_cart
from django.views.decorators.http import require_POST
from decimal import Decimal, ROUND_HALF_UP
from authenticate.models import Address
from orders.models import Order,OrderItem
from django.contrib import messages
from authenticate.models import Address
from django.views.decorators.cache import never_cache
from django.urls import reverse
from coupons.models import Coupon
from django.utils import timezone
from django.db import transaction
from wallet.models import Wallet
from wallet.services import debit_wallet
from coupons.services import apply_coupon_for_user
import re
from decimal import Decimal
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.views.decorators.cache import never_cache
from offers.utils import get_best_offer_for_product, apply_offer
from products.models import ProductVariants

@never_cache
def cart_page(request):
    if not request.user.is_authenticated or request.user.is_superuser:
        return redirect("user_login")

    cart = get_user_cart(request.user)
    now = timezone.now()
    available_coupons = Coupon.objects.filter(
        is_active=True,
        valid_from__lte=now,
        valid_to__gte=now,
        usage_limit__gt=0,
        min_order_amount__lte=cart.item_subtotal

    )
    revalidate_cart_prices(cart)

    recalculate_cart_totals(cart)

    context = {
        "cart": cart,
        "cart_items": cart.cart_items.all(),
        "sub_total": cart.item_subtotal,
        "tax": cart.tax,
        "shipping_fee": cart.shipping_fee,
        "total": cart.total_price,
        "available_coupons": available_coupons,
        "breadcrumbs": [
            {"label": "Home", "url": "/"},
            {"label": "Cart", "url": ""}
        ]   
    }

    return render(request, "cart_page.html", context)

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

    try:
        quantity = int(quantity)
    except (TypeError, ValueError):
        quantity = 1

    quantity = max(quantity, 1)

    if variant_id:
       
        item.variant = ProductVariants.objects.get(id=variant_id)

      
        offer = get_best_offer_for_product(item.variant.product)
        item.unit_price = (
            apply_offer(item.variant.price, offer)
            if offer else item.variant.price
        )
    max_limit = min(item.variant.stock, 5)
    if quantity > max_limit:
        quantity = max_limit
        errors["quantity"] = f"Only {max_limit} units available."

    item.quantity = quantity

    gst_rate = Decimal(str(getattr(item.variant, "gst_rate", 18)))
    unit_tax = (item.unit_price * gst_rate / Decimal("100")).quantize(
        Decimal("0.01")
    )

    item.tax_amount = unit_tax * quantity
    item.total_price = (item.unit_price * quantity) + item.tax_amount

    item.save()
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


from django.views.decorators.cache import never_cache
from django.shortcuts import render, redirect
from django.urls import reverse
from cart.models import Cart, CartItems


@never_cache
def checkout_page(request):
    if not request.user.is_authenticated or request.user.is_superuser:
        return redirect("user_login")

    addresses = Address.objects.filter(user=request.user)

    cart = Cart.objects.get(user=request.user)
    cart_items = CartItems.objects.filter(cart=cart)
    wallet = Wallet.objects.filter(user=request.user).first()

    context = {
        "addresses": addresses,
        "cart_items": cart_items,
        "subtotal": cart.item_subtotal,
        "tax": cart.tax,
        "shipping_fee": cart.shipping_fee,
        "coupon": cart.applied_coupon,
        "coupon_discount": cart.coupon_discount,
        "total_price": cart.total_price,
        "cart": cart,
        "wallet": wallet,

        "breadcrumbs": [
            {"label": "Home", "url": "/"},
            {"label": "Cart", "url": reverse("cart_page")},
            {"label": "Checkout", "url": ""},
        ],
    }

    return render(request, "checkout.html", context)
from decimal import Decimal, ROUND_HALF_UP
from decimal import Decimal, ROUND_HALF_UP
from django.shortcuts import redirect, get_object_or_404
from django.contrib import messages
from django.db import transaction
from django.views.decorators.cache import never_cache

@never_cache
@transaction.atomic
def place_order(request):

    if not request.user.is_authenticated or request.user.is_superuser:
        return redirect("user_login")

    if request.method != "POST":
        return redirect("checkout_page")

    user = request.user
    selected_address_id = request.POST.get("selected_address")
    payment_method = request.POST.get("payment_method")

    if not selected_address_id:
        messages.error(request, "Please select a delivery address")
        return redirect("checkout_page")

    address = get_object_or_404(Address, id=selected_address_id, user=user)

    cart = Cart.objects.select_for_update().get(user=user)
    cart_items = CartItems.objects.select_for_update().filter(cart=cart)

    if not cart_items.exists():
        messages.error(request, "Your cart is empty")
        return redirect("cart_page")

    out_of_stock = False

    for i in cart_items:
        if i.quantity > i.variant.stock:
            i.delete()
            out_of_stock = True

    if out_of_stock:
        messages.error(
            request,
            "Some items were removed from your cart because they are out of stock. Please review your cart."
        )
        return redirect("cart_page")


    order = Order.objects.create(
        user=user,

        address=address,
        full_name=address.full_name,
        phone=address.phone_number,
        address_line1=address.address_line1,
        address_line2=address.address_line2,
        city=address.city,
        state=address.state,
        country=address.country,
        pincode=address.pincode,

        payment_method=payment_method.lower(),
        subtotal=cart.item_subtotal,
        tax=cart.tax,
        shipping_fee=cart.shipping_fee,
        coupon=cart.applied_coupon,
        coupon_discount=cart.coupon_discount,
        total=cart.total_price,
        payment_status="pending",
    )

    order_base = cart.total_price + cart.coupon_discount
    coupon_discount = cart.coupon_discount or Decimal("0.00")

    count = 1
    for cart_item in cart_items:
        item_price = cart_item.total_price

        if coupon_discount > 0 and order_base > 0:
            coupon_share = (
                (item_price / order_base) * coupon_discount
            ).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        else:
            coupon_share = Decimal("0.00")

        net_paid_amount = (
            item_price - coupon_share
        ).quantize(Decimal("0.01"))

        order_item = OrderItem.objects.create(
            order=order,
            product=cart_item.variant.product,
            variant=cart_item.variant,
            quantity=cart_item.quantity,
            price=item_price,
            coupon_share=coupon_share,
            net_paid_amount=net_paid_amount,
        )

        order_item.sub_order_id = f"{order.order_number}-{count}"
        order_item.save(update_fields=["sub_order_id"])

        variant = cart_item.variant
        variant.stock -= cart_item.quantity
        variant.save(update_fields=["stock"])

        count += 1

    if payment_method == "COD":
        order.payment_status = "paid"
        order.payment_method = "cod"
        order.save(update_fields=["payment_status", "payment_method"])

    elif payment_method == "WALLET":
        debit_wallet(
            user=user,
            amount=order.total,
            order=order,
            description="Order payment via wallet"
        )
        order.payment_status = "paid"
        order.payment_method = "wallet"
        order.save(update_fields=["payment_status", "payment_method"])

    elif payment_method == "Razorpay":
        order.payment_method = "razorpay"
        order.save(update_fields=["payment_method"])

    cart_items.delete()
    cart.applied_coupon = None
    cart.coupon_discount = Decimal("0.00")
    cart.item_subtotal = Decimal("0.00")
    cart.tax = Decimal("0.00")
    cart.shipping_fee = Decimal("0.00")
    cart.total_price = Decimal("0.00")
    cart.save()

    if payment_method == "Razorpay":
        return redirect("start_payment", uuid=order.uuid)

    return redirect("order_placed", uuid=order.uuid)


@never_cache
def order_placed(request, uuid):
    if not request.user.is_authenticated or request.user.is_superuser:
        return redirect("landing_page")
    order = Order.objects.get(uuid=uuid, user=request.user)
    return render(request, "order_placed.html", {"order": order})


import re

@never_cache
def add_address(request):

    if not request.user.is_authenticated or request.user.is_superuser:
        return redirect("landing_page")

    errors = {}

    if request.method == "POST":
        FULLNAME_REGEX = re.compile(r'^[A-Za-z .]+$')
        PHONE_REGEX = re.compile(r'^[6-9]\d{9}$')
        CITY_STATE_REGEX = re.compile(r'^[A-Za-z ]+$')
        PINCODE_REGEX = re.compile(r'^\d{6}$')

        full_name = request.POST.get("full_name", "").strip()
        phone = request.POST.get("phone_number", "").strip()
        line1 = request.POST.get("address_line1", "").strip()
        line2 = request.POST.get("address_line2", "").strip()
        city = request.POST.get("city", "").strip()
        state = request.POST.get("state", "").strip()
        pincode = request.POST.get("pincode", "").strip()

        if not full_name:
            errors["full_name"] = "Full name is required."
        elif len(full_name) < 3:
            errors["full_name"] = "Full name must be at least 3 characters."
        elif not FULLNAME_REGEX.match(full_name):
            errors["full_name"] = "Name can contain only letters, spaces, and dot (.)."

        if not phone:
            errors["phone_number"] = "Phone number is required."
        elif not PHONE_REGEX.match(phone):
            errors["phone_number"] = "Enter a valid 10-digit phone number."

        if not line1:
            errors["address_line1"] = "Address line is required."
        elif len(line1) < 5:
            errors["address_line1"] = "Address must be at least 5 characters."

        if not city:
            errors["city"] = "City is required."
        elif not CITY_STATE_REGEX.match(city):
            errors["city"] = "City can contain only letters and spaces."

        if not state:
            errors["state"] = "State is required."
        elif not CITY_STATE_REGEX.match(state):
            errors["state"] = "State can contain only letters and spaces."

        if not pincode:
            errors["pincode"] = "Pincode is required."
        elif not PINCODE_REGEX.match(pincode):
            errors["pincode"] = "Enter a valid 6-digit pincode."

        if errors:
            return render(request, "add_address.html", {"errors": errors})

        Address.objects.create(
            user=request.user,
            full_name=full_name,
            phone_number=phone,
            address_line1=line1,
            address_line2=line2,
            city=city,
            state=state,
            country="India",
            pincode=pincode,
        )

        messages.success(request, "Address added successfully.")
        return redirect("checkout_page")

    return render(request, "add_address.html")


import re

@never_cache
def edit_address(request, uuid):

    if not request.user.is_authenticated or request.user.is_superuser:
        return redirect("landing_page")

    address = get_object_or_404(Address, uuid=uuid, user=request.user)
    errors = {}

    if request.method == "POST":
        FULLNAME_REGEX = re.compile(r'^[A-Za-z .]+$')
        PHONE_REGEX = re.compile(r'^[6-9]\d{9}$')
        CITY_STATE_REGEX = re.compile(r'^[A-Za-z ]+$')
        PINCODE_REGEX = re.compile(r'^\d{6}$')

        full_name = request.POST.get("full_name", "").strip()
        phone = request.POST.get("phone_number", "").strip()
        line1 = request.POST.get("address_line1", "").strip()
        line2 = request.POST.get("address_line2", "").strip()
        city = request.POST.get("city", "").strip()
        state = request.POST.get("state", "").strip()
        pincode = request.POST.get("pincode", "").strip()

        if not full_name:
            errors["full_name"] = "Full name is required."
        elif len(full_name) < 3:
            errors["full_name"] = "Full name must be at least 3 characters."
        elif not FULLNAME_REGEX.match(full_name):
            errors["full_name"] = "Name can contain only letters, spaces, and dot (.)."

        if not phone:
            errors["phone_number"] = "Phone number is required."
        elif not PHONE_REGEX.match(phone):
            errors["phone_number"] = "Enter a valid 10-digit phone number."

        if not line1:
            errors["address_line1"] = "Address line is required."
        elif len(line1) < 5:
            errors["address_line1"] = "Address must be at least 5 characters."

        if not city:
            errors["city"] = "City is required."
        elif not CITY_STATE_REGEX.match(city):
            errors["city"] = "City can contain only letters and spaces."

        if not state:
            errors["state"] = "State is required."
        elif not CITY_STATE_REGEX.match(state):
            errors["state"] = "State can contain only letters and spaces."

        if not pincode:
            errors["pincode"] = "Pincode is required."
        elif not PINCODE_REGEX.match(pincode):
            errors["pincode"] = "Enter a valid 6-digit pincode."

        if errors:
            return render(
                request,
                "edit_address.html",
                {"address": address, "errors": errors}
            )

        address.full_name = full_name
        address.phone_number = phone
        address.address_line1 = line1
        address.address_line2 = line2
        address.city = city
        address.state = state
        address.pincode = pincode
        address.save()

        messages.success(request, "Address updated successfully.")
        return redirect("checkout_page")

    return render(request, "edit_address.html", {"address": address})



def apply_coupon(request):
    if not request.user.is_authenticated:
        return redirect("user_login")

    if request.method == "POST":
        code = request.POST.get("coupon_code", "").strip().upper()
        cart = get_user_cart(request.user)

        try:
            coupon = Coupon.objects.get(code=code)

            if not coupon.is_valid():
                raise Exception("Invalid or expired coupon")

            if cart.item_subtotal < coupon.min_order_amount:
                raise Exception("Minimum order amount not met")

            success, message = apply_coupon_for_user(request.user, coupon)
            if not success:
                raise Exception(message)

            cart.applied_coupon = coupon
            cart.save()

            recalculate_cart_totals(cart)

            messages.success(
                request,
                f"Coupon {coupon.code} applied successfully"
            )

        except Coupon.DoesNotExist:
            messages.error(request, "Coupon not found")

        except Exception as e:
            messages.error(request, str(e))

    return redirect("cart_page")


@require_POST
def remove_coupon(request):
    if not request.user.is_authenticated:
        return redirect("user_login")

    cart = Cart.objects.filter(user=request.user).first()
    coupon = Coupon.objects.filter()

    if not cart or not cart.applied_coupon:
        messages.warning(request, "No coupon applied to remove.")
        return redirect("cart_page")

    cart.applied_coupon = None
    cart.coupon_discount = 0
    cart.save(update_fields=["applied_coupon", "coupon_discount"])

    recalculate_cart_totals(cart)

    messages.success(request, "Coupon removed successfully.")
    return redirect("cart_page")

