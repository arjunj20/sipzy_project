from django.shortcuts import render

from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.contrib import messages
from .models import Coupon


def coupon_list(request):
    if not request.user.is_authenticated or not request.user.is_superuser:
        return redirect("admin_login")

    coupons = Coupon.objects.all()
    return render(request, "admin_coupon_list.html", {"coupons": coupons})

def add_coupon(request):
    if not request.user.is_authenticated or not request.user.is_superuser:
        return redirect("admin_login")

    errors = {}

    if request.method == "POST":
        code = request.POST.get("code", "").strip().upper()
        discount_amount = request.POST.get("discount_amount")
        min_order_amount = request.POST.get("min_order_amount")
        valid_from_raw = request.POST.get("valid_from")
        valid_to_raw = request.POST.get("valid_to")
        usage_limit = request.POST.get("usage_limit")
        is_active = request.POST.get("is_active") == "on"
        if not code:
            errors["code"] = "Coupon code is required"
        elif Coupon.objects.filter(code=code).exists():
            errors["code"] = "Coupon code already exists"

        try:
            discount_amount = float(discount_amount)
            if discount_amount <= 0:
                errors["discount_amount"] = "Discount must be greater than 0"
        except:
            errors["discount_amount"] = "Invalid discount amount"

        try:
            min_order_amount = float(min_order_amount)
            if min_order_amount <= 0:
                errors["min_order_amount"] = "Minimum order must be greater than 0"
        except:
            errors["min_order_amount"] = "Invalid minimum order amount"

        if (
            "discount_amount" not in errors
            and "min_order_amount" not in errors
            and discount_amount > min_order_amount
        ):
            errors["discount_amount"] = "Discount cannot exceed minimum order amount"

        try:
            usage_limit = int(usage_limit)
            if usage_limit < 1:
                errors["usage_limit"] = "Usage limit must be at least 1"
        except:
            errors["usage_limit"] = "Invalid usage limit"

        try:
            valid_from = timezone.make_aware(
                timezone.datetime.fromisoformat(valid_from_raw)
            )
            valid_to = timezone.make_aware(
                timezone.datetime.fromisoformat(valid_to_raw)
            )

            if valid_from >= valid_to:
                errors["date"] = "Valid To must be after Valid From"

        except:
            errors["date"] = "Invalid date values"
        if not errors:
            Coupon.objects.create(
                code=code,
                discount_amount=discount_amount,
                min_order_amount=min_order_amount,
                valid_from=valid_from,
                valid_to=valid_to,
                usage_limit=usage_limit,
                is_active=is_active,
            )
            messages.success(request, "Coupon created successfully")
            return redirect("coupon_list")

    return render(request, "admin_add_coupon.html", {
        "errors": errors
    })

def delete_coupon(request, coupon_id):
    if not request.user.is_authenticated or not request.user.is_superuser:
        return redirect("admin_login")

    coupon = get_object_or_404(Coupon, id=coupon_id)

    if coupon.used_count > 0:
        coupon.is_active = False
        coupon.save()
        messages.warning(
            request,
            "Coupon has been used already. It was deactivated instead of deleted."
        )
    else:
        coupon.delete()
        messages.success(request, "Coupon deleted successfully")

    return redirect("coupon_list")
