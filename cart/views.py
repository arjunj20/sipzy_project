from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from .utils import get_user_cart,recalculate_cart_totals
from django.http import JsonResponse
from .models import CartItems,Cart
from .utils import get_user_cart
from django.views.decorators.http import require_POST
from decimal import Decimal
from authenticate.models import Address
from orders.models import Order,OrderItem
from django.contrib import messages
from authenticate.models import Address



def cart_page(request):

    if not request.user.is_authenticated or request.user.is_superuser:
        return redirect("user_login")

    cart = get_user_cart(request.user)
    items = cart.cart_items.select_related("variant", "variant__product")
    for i in items:
        if not i.variant.product.is_active or i.variant.stock == 0:
            i.delete()
    items = cart.cart_items.select_related("variant", "variant__product")

    recalculate_cart_totals(cart)

    context = {
        "cart": cart,
        "cart_items": items,
        "sub_total": cart.item_subtotal,
        "shipping_fee": cart.shipping_fee,
        "total": cart.total_price,
        "tax": cart.tax,
    }

    return render(request, "cart_page.html", context)


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

    try:
        quantity = int(quantity)
    except:
        quantity = 1

    if quantity < 1:
        quantity = 1

    if variant_id:
        item.variant_id = variant_id

    max_limit = min(item.variant.stock, 5)

    if quantity > max_limit:
        quantity = max_limit
        errors["quantity"] = f"Oops! You’ve reached the limit. Only {max_limit} units are allowed."

    item.quantity = quantity
    unit_price = Decimal(str(item.variant.price))
    gst_rate = Decimal(str(item.variant.gst_rate))

    unit_tax = unit_price * (gst_rate / Decimal('100'))
    item.tax_amount = round(unit_tax * quantity, 2)

    item.total_price = (unit_price * quantity) + Decimal(str(item.tax_amount))
    item.save()

    recalculate_cart_totals(cart)

    return JsonResponse({
        "success": True,
        "item_total": float(item.total_price),
        "unit_price": float(item.variant.price),
        "subtotal": float(cart.item_subtotal),
        "shipping": float(cart.shipping_fee),
        "tax": float(cart.tax),
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
    }
    return render(request, "checkout.html" , context)


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

def order_placed(request, order_id):
    order = Order.objects.get(id=order_id, user=request.user)
    return render(request, "order_placed.html", {"order": order})


def add_address(request):
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


def edit_address(request, id):
    address = get_object_or_404(Address, id=id, user=request.user)

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
