from django.shortcuts import render, redirect, get_object_or_404    
from .models import Order,OrderItem
from django.template.loader import render_to_string
from django.http import HttpResponse
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from django.contrib import messages
import tempfile

from django.views.decorators.cache import never_cache

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
        "orders": orders
    })

@never_cache
def order_detail(request, uuid):

    if not request.user.is_authenticated or request.user.is_superuser:
        return redirect("landing_page")

    order = get_object_or_404(Order, uuid=uuid, user=request.user)

    # 🔥 ADD THIS LINE (THIS IS THE FIX)
    order.recalculate_totals()

    items = order.items.all()  

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

    items = order.items.all()  # related_name on OrderItem
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
    p.drawString(370, y, "Price")
    p.drawString(450, y, "Total")

    y -= 20
    p.setFont("Helvetica", 12)

    # 🔹 Items
    for item in items:
        if y < 80:
            p.showPage()
            y = height - 50

        p.drawString(30, y, item.product.name)
        p.drawString(230, y, item.variant.variant if item.variant else "-")
        p.drawString(330, y, str(item.quantity))
        p.drawString(370, y, f"₹{item.price}")
        p.drawString(450, y, f"₹{item.price * item.quantity}")
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

    y -= 20
    p.setFont("Helvetica-Bold", 14)
    p.drawString(330, y, "TOTAL:")
    p.drawString(450, y, f"₹{order.total}")

    p.showPage()
    p.save()

    return response

@never_cache
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

    try:

        item.status = "cancelled"
        item.cancel_reason = reason
        item.save(update_fields=["status", "cancel_reason"])
        if item.variant:
            item.variant.stock += item.quantity
            item.variant.save(update_fields=["stock"])

        item.order.recalculate_totals()

        messages.success(request, "Item cancelled successfully.")

    except Exception as e:
        print("CANCEL ERROR:", e)
        messages.error(request, "Something went wrong while cancelling the item.")

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
