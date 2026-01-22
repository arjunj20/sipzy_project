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
from django.db.models import Sum

from django.views.decorators.cache import never_cache
from wallet.models import Wallet, WalletTransaction
from wallet.services import refund_to_wallet
from django.db import transaction
from decimal import Decimal
from django.core.paginator import Paginator
from django.shortcuts import render, redirect
from django.urls import reverse
from django.views.decorators.cache import never_cache
from reportlab.lib.colors import red, green, black


@never_cache
def order_list(request):
    if not request.user.is_authenticated or request.user.is_superuser:
        return redirect("landing_page")
        
    q = request.GET.get('q', '')
    if q:
        order_qs = Order.objects.filter(order_number__icontains=q, user=request.user).order_by("-created_at")
    else:
        order_qs = Order.objects.filter(user=request.user).order_by("-created_at")

    paginator = Paginator(order_qs, 10) 
    page_number = request.GET.get('page')
    orders = paginator.get_page(page_number)

    return render(request, "orders/order_list.html", {
        "orders": orders,
        "query": q,
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

    items = order.items.filter(status="delivered")

    if not items.exists():
        messages.error(
            request,
            "Invoice is available only after delivery."
        )
        return redirect("order_detail", uuid=order.uuid)

    full_name = order.full_name or ""
    address_line1 = order.address_line1 or "Address not available"
    city = order.city or ""
    state = order.state or ""
    pincode = order.pincode or ""

    subtotal = order.items.filter(status="delivered").aggregate(
    total=Sum("net_paid_amount")
        )["total"] or Decimal("0.00")


    total_coupon = items.aggregate(
        total=Sum("coupon_share")
    )["total"] or Decimal("0.00")

    GST_RATE = Decimal("0.18")
    tax = (subtotal * GST_RATE).quantize(Decimal("0.01"))
    shipping_fee = Decimal("0.00")
    total = subtotal + shipping_fee

    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = (
        f'attachment; filename="Invoice_{order.order_number}.pdf"'
    )

    p = canvas.Canvas(response, pagesize=A4)
    width, height = A4
    y = height - 50

    p.setFont("Helvetica-Bold", 20)
    p.drawString(30, y, "INVOICE")

    y -= 40
    p.setFont("Helvetica", 12)
    p.drawString(30, y, f"Order Number : {order.order_number}")
    y -= 20
    p.drawString(
        30,
        y,
        f"Order Date   : {order.created_at.strftime('%d-%m-%Y %H:%M')}"
    )

    y -= 40
    p.setFont("Helvetica-Bold", 12)
    p.drawString(30, y, "Billing Address:")

    y -= 20
    p.setFont("Helvetica", 12)
    p.drawString(30, y, full_name)
    y -= 20
    p.drawString(30, y, address_line1)
    y -= 20
    p.drawString(30, y, f"{city}, {state}".strip(", "))
    y -= 20
    p.drawString(30, y, pincode)

    y -= 40
    p.setFont("Helvetica-Bold", 12)
    p.drawString(30, y, "Product")
    p.drawString(210, y, "Variant")
    p.drawString(300, y, "Qty")
    p.setFillColor(green)
    p.drawString(340, y, "Coupon")
    p.setFillColor(black)
    p.drawString(420, y, "Paid")

    y -= 20
    p.setFont("Helvetica", 12)

    for item in items:
        if y < 80:
            p.showPage()
            y = height - 50
            p.setFont("Helvetica", 12)

        p.setFillColor(black)
        p.drawString(30, y, item.product.name if item.product else "-")
        p.drawString(
            210,
            y,
            item.variant.variant if item.variant else "-"
        )
        p.drawString(300, y, str(item.quantity))
        p.setFillColor(green)
        p.drawString(340, y, f"-₹{item.coupon_share}")
        p.setFillColor(black)
        p.drawString(420, y, f"₹{item.net_paid_amount}")
        y -= 20

    y -= 30
    p.setFont("Helvetica-Bold", 12)
    p.drawString(330, y, "Subtotal:")
    p.drawString(460, y, f"₹{subtotal}")

    y -= 20
    p.setFillColor(green)
    p.drawString(330, y, "Coupon Discount:")
    p.drawString(460, y, f"-₹{total_coupon}")
    p.setFillColor(black)

    y -= 20
    p.drawString(330, y, "Tax (GST 18%):")
    p.drawString(460, y, f"₹{tax}")

    y -= 20
    p.drawString(330, y, "Shipping:")
    p.drawString(460, y, f"₹{shipping_fee}")

    y -= 30
    p.setFont("Helvetica-Bold", 14)
    p.drawString(330, y, "TOTAL:")
    p.drawString(460, y, f"₹{total}")

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
    
    if order.payment_status != "paid":
        messages.error(request, "Action allowed only for paid orders")
        return redirect("order_detail", uuid=order.uuid)

    
    
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
