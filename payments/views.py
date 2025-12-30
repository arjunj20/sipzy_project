from django.shortcuts import get_object_or_404, render, redirect
import razorpay
from django.conf import settings
from orders.models import Order
import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from orders.models import Order

import razorpay
from django.conf import settings
from django.shortcuts import get_object_or_404, redirect, render
from orders.models import Order

def start_payment(request, uuid):
    # 🔐 Fetch order securely using UUID
    order = get_object_or_404(
        Order,
        uuid=uuid,
        user=request.user
    )

    # Prevent double payment
    if order.payment_status == "paid":
        return redirect(
            "payments:payment_success",
            order.uuid
        )

    client = razorpay.Client(
        auth=(
            settings.RAZORPAY_KEY_ID,
            settings.RAZORPAY_KEY_SECRET
        )
    )

    # 🔗 Create Razorpay order and attach order_number
    razorpay_order = client.order.create({
        "amount": int(order.total * 100),  # INR → paise
        "currency": "INR",
        "receipt": order.order_number,  # ⭐ IMPORTANT
        "payment_capture": 1
    })

    # Save Razorpay order id
    order.razorpay_order_id = razorpay_order["id"]
    order.save(update_fields=["razorpay_order_id"])

    return render(
        request,
        "payments/checkout.html",
        {
            "order": order,
            "razorpay_key": settings.RAZORPAY_KEY_ID,
            "razorpay_order_id": razorpay_order["id"],
            "amount": order.total,
        }
    )



@csrf_exempt
def verify_payment(request):
    if request.method != "POST":
        return JsonResponse({"status": "invalid"}, status=400)

    data = json.loads(request.body)

    razorpay_order_id = data.get("razorpay_order_id")
    razorpay_payment_id = data.get("razorpay_payment_id")
    razorpay_signature = data.get("razorpay_signature")
    order_uuid = data.get("order_uuid")

    order = get_object_or_404(Order, uuid=order_uuid)

    client = razorpay.Client(
        auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET)
    )

    try:
        # 🔐 SIGNATURE VERIFICATION
        client.utility.verify_payment_signature({
            "razorpay_order_id": razorpay_order_id,
            "razorpay_payment_id": razorpay_payment_id,
            "razorpay_signature": razorpay_signature,
        })

        # ✅ PAYMENT SUCCESS
        order.payment_status = "paid"
        order.razorpay_payment_id = razorpay_payment_id
        order.save(update_fields=["payment_status", "razorpay_payment_id"])

        return JsonResponse({"status": "success"})

    except razorpay.errors.SignatureVerificationError:
        # ❌ PAYMENT FAILED
        order.payment_status = "failed"
        order.save(update_fields=["payment_status"])

        return JsonResponse({"status": "failed"}, status=400)
    

def payment_success(request, uuid):
    order = get_object_or_404(Order, uuid=uuid, user=request.user)
    return render(request, "payments/success.html", {"order": order})


def payment_failure(request, uuid):
    order = get_object_or_404(Order, uuid=uuid, user=request.user)
    return render(request, "payments/failure.html", {"order": order})

# Create your views here.
