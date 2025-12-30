from django.shortcuts import render, redirect, get_object_or_404    
from .models import Order,OrderItem
from django.template.loader import render_to_string
from django.http import HttpResponse
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from django.contrib import messages
import tempfile
from django.urls import reverse

from django.views.decorators.cache import never_cache
from wallet.models import Wallet, WalletTransaction
from wallet.services import refund_to_wallet
from django.db import transaction
from decimal import Decimal

@never_cache
def order_list(request):

    if not request.user.is_authenticated or request.user.is_superuser:
        return redirect("landing_page")
        
    
    q = request.GET.get('q', '')

    if q:
        orders = Order.objects.filter(order_number__icontains=q, user=request.user)
    else:
        orders = Order.objects.filter(user=request.user).order_by("-created_at")

    return render(request, "orders/order_list.html", {
        "orders": orders,
        "breadcrumbs": [
            {"label": "Home", "url": "/"},
            {"label": "My Profile", "url": reverse("user_profile")},
            {"label": "My Orders", "url": ""}
        ]
    })
@never_cache
def order_detail(request, uuid):

    if not request.user.is_authenticated or request.user.is_superuser:
        return redirect("landing_page")

    order = get_object_or_404(
        Order,
        uuid=uuid,
        user=request.user
    )

    items = order.items.all()

    # 🔥 ADD THIS
    for item in items:
        item.net_paid = item.price - item.coupon_share

    return render(request, "orders/order_detail.html", {
        "order": order,
        "items": items,
    })


def order_invoice(request, order_id):
    order = get_object_or_404(
        Order,
        id=order_id,
        user=request.user
    )

    items = order.items.all()
    user = request.user

    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = (
        f'attachment; filename="Invoice_{order.order_number}.pdf"'
    )

    p = canvas.Canvas(response, pagesize=A4)
    width, height = A4
    y = height - 50

    # 🔹 Header
    p.setFont("Helvetica-Bold", 20)
    p.drawString(30, y, "INVOICE")

    y -= 40
    p.setFont("Helvetica", 12)
    p.drawString(30, y, f"Order Number : {order.order_number}")
    y -= 20
    p.drawString(30, y, f"Order Date   : {order.created_at.strftime('%d-%m-%Y %H:%M')}")

    # 🔹 Billing Address
    y -= 40
    p.setFont("Helvetica-Bold", 12)
    p.drawString(30, y, "Billing Address:")
    y -= 20
    p.setFont("Helvetica", 12)
    p.drawString(30, y, user.fullname)
    y -= 20
    p.drawString(30, y, order.address.address_line1)
    y -= 20
    p.drawString(30, y, f"{order.address.city}, {order.address.state}")
    y -= 20
    p.drawString(30, y, order.address.pincode)

    # 🔹 Table Header
    y -= 40
    p.setFont("Helvetica-Bold", 12)
    p.drawString(30, y, "Product")
    p.drawString(230, y, "Variant")
    p.drawString(330, y, "Qty")
    p.drawString(380, y, "Line Total")

    y -= 20
    p.setFont("Helvetica", 12)

    # 🔹 Items (NO MULTIPLICATION)
    for item in items:
        if y < 80:
            p.showPage()
            y = height - 50

        p.drawString(30, y, item.product.name)
        p.drawString(230, y, item.variant.variant if item.variant else "-")
        p.drawString(330, y, str(item.quantity))
        p.drawString(380, y, f"₹{item.price}")  # ✅ LINE TOTAL
        y -= 20

    # 🔹 Totals
    y -= 30
    p.setFont("Helvetica-Bold", 12)

    p.drawString(330, y, "Subtotal:")
    p.drawString(450, y, f"₹{order.subtotal}")

    y -= 20
    p.drawString(330, y, "Shipping:")
    p.drawString(450, y, f"₹{order.shipping_fee}")

    y -= 20
    p.drawString(330, y, "Tax:")
    p.drawString(450, y, f"₹{order.tax}")

    # 🔹 Coupon
    if order.coupon:
        y -= 20
        p.setFillColorRGB(0, 0.6, 0)
        p.drawString(
            330,
            y,
            f"Coupon ({order.coupon.code}):"
        )
        p.drawString(
            450,
            y,
            f"-₹{order.coupon_discount}"
        )
        p.setFillColorRGB(0, 0, 0)

    y -= 30
    p.setFont("Helvetica-Bold", 14)
    p.drawString(330, y, "TOTAL:")
    p.drawString(450, y, f"₹{order.total}")

    p.showPage()
    p.save()

    return response


@never_cache
@transaction.atomic
def cancel_item(request, uuid):
    if not request.user.is_authenticated or request.user.is_superuser:
        return redirect("landing_page")

    if request.method != "POST":
        return redirect("order_list")

    item = get_object_or_404(
        OrderItem,
        uuid=uuid,
        order__user=request.user
    )


    if item.status in ["delivered", "cancelled", "returned"]:
        messages.error(request, "This item cannot be cancelled.")
        return redirect("order_detail", uuid=item.order.uuid)

    reason = request.POST.get("reason", "").strip()
    if not reason:
        messages.error(request, "Cancellation reason is required.")
        return redirect("order_detail", uuid=item.order.uuid)
    
    order = item.order
    
    try:

        item.status = "cancelled"
        item.cancel_reason = reason
        item.save(update_fields=["status", "cancel_reason"])
        if item.variant:
            item.variant.stock += item.quantity
            item.variant.save(update_fields=["stock"])

        if order.payment_method != "cod" and order.payment_status == "paid":
            already_refunded = WalletTransaction.objects.filter(
                order=order,
                description__icontains=(str(item.sub_order_id))
            ).exists()

            if not already_refunded:

                refund_amount = max(
                    item.price - item.coupon_share,
                    Decimal("0.00")
                )

                refund_to_wallet(
                    user=order.user,
                    amount=refund_amount,
                    order=order,
                    description=f"Refund for cancelled item {item.sub_order_id}"


                )

        item.order.recalculate_totals()

        messages.success(request, "Item cancelled successfully.")

    except Exception as e:
        print("CANCEL ERROR:", e)
        messages.error(request, "Something went wrong while cancelling the item.")
        raise

    return redirect("order_detail", uuid=item.order.uuid)


from django.shortcuts import get_object_or_404, redirect
from .models import OrderItem, ReturnRequest

@never_cache
def submit_return_request(request, uuid):

    if not request.user.is_authenticated or request.user.is_superuser:
        return redirect("landing_page")

    if request.method != "POST":
        return redirect("error_page")

    item = get_object_or_404(
        OrderItem,
        uuid=uuid,
        order__user=request.user
    )

    if item.status != "delivered":
        messages.warning(request, "This item cannot be returned.")
        return redirect("order_detail", uuid=item.order.uuid)

    if ReturnRequest.objects.filter(order_item=item).exists():
        messages.warning(request, "Return already requested.")
        return redirect("order_detail", uuid=item.order.uuid)

    ReturnRequest.objects.create(
        order_item=item,
        reason=request.POST.get("reason")
    )


    OrderItem.objects.filter(pk=item.pk).update(
        status="return_requested"
    )

    messages.success(
        request,
        "Return request submitted. Waiting for admin approval."
    )

    return redirect("order_detail", uuid=item.order.uuid)
