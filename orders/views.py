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
    items = order.items.all()  

    return render(request, "orders/order_detail.html", {
        "order": order,
        "items": items,
    })

def item_invoice(request, item_id):

    item = get_object_or_404(OrderItem, id=item_id, order__user=request.user)
    order = item.order
    user = request.user

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="Invoice_{item.sub_order_id}.pdf"'

    p = canvas.Canvas(response, pagesize=A4)
    width, height = A4

    # Title
    p.setFont("Helvetica-Bold", 20)
    p.drawString(30, height - 50, "INVOICE")

    # Order Information
    p.setFont("Helvetica", 12)
    p.drawString(30, height - 100, f"Item Order ID : {item.sub_order_id}")
    p.drawString(30, height - 120, f"Order Number  : {order.order_number}")
    p.drawString(30, height - 140, f"Date          : {order.created_at.strftime('%d-%m-%Y %H:%M')}")

    # Billing Details
    p.drawString(30, height - 180, "Billing To:")
    p.drawString(50, height - 200, f"{user.fullname}")
    p.drawString(50, height - 220, f"{order.address.address_line1}")
    p.drawString(50, height - 240, f"{order.address.city}, {order.address.state}")
    p.drawString(50, height - 260, f"{order.address.pincode}")

    # Product Table Header
    p.setFont("Helvetica-Bold", 12)
    p.drawString(30, height - 300, "Product")
    p.drawString(200, height - 300, "Variant")
    p.drawString(300, height - 300, "Qty")
    p.drawString(350, height - 300, "Price")
    p.drawString(420, height - 300, "Total")

    # Product Row
    p.setFont("Helvetica", 12)
    p.drawString(30, height - 330, item.product.name)
    p.drawString(200, height - 330, item.variant.variant if item.variant else "-")
    p.drawString(300, height - 330, str(item.quantity))
    p.drawString(350, height - 330, f"₹{item.price}")
    p.drawString(420, height - 330, f"₹{item.price * item.quantity}")

    # Final Total
    p.setFont("Helvetica-Bold", 14)
    p.drawString(30, height - 380, f"TOTAL AMOUNT: ₹{item.price * item.quantity}")

    p.showPage()
    p.save()

    return response

@never_cache
def cancel_item(request, item_id):
    if not request.user.is_authenticated or request.user.is_superuser:
        return redirect("landing_page")
    try:
        item = OrderItem.objects.get(id=item_id, order__user=request.user)
    except OrderItem.DoesNotExist:
        messages.error(request, "Item not found or unauthorized access.")
        return redirect("order_list") 

    try:
        if item.status in ["delivered", "cancelled"]:
            messages.error(request, "This item cannot be cancelled.")
            return redirect("order_detail", id=item.order.id)
        item.status = "cancelled"
        item.save()
        if item.variant:
            item.variant.stock += item.quantity
            item.variant.save(update_fields=["stock"])
        
        item.order.recalculate_totals()

        messages.success(request, "Item cancelled successfully.")

    except Exception as e:
        print("CANCEL ERROR:", e)
        messages.error(request, "Something went wrong while cancelling the item.")
    return redirect("order_detail", id=item.order.id)


from django.shortcuts import get_object_or_404, redirect
from .models import OrderItem, ReturnRequest


@never_cache
def submit_return_request(request, item_id):

    if not request.user.is_authenticated or request.user.is_superuser:
        return redirect("landing_page")
    
    if request.method != "POST":
        return redirect("error_page") 

    item = get_object_or_404(OrderItem, id=item_id)

    if hasattr(item, "return_request"):
        messages.warning(request, "Return request already submitted for this item.")
        return redirect("order_detail", order_id=item.order.id)

    reason = request.POST.get("reason")
    ReturnRequest.objects.create(order_item=item, reason=reason)

    item.status = "returned"
    item.save(update_fields=["status"])

    messages.success(request, "Your return request has been submitted.")
    return redirect("order_detail", id=item.order.id)

