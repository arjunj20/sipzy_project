from django.shortcuts import render

from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.contrib import messages
from .models import Coupon
from decimal import Decimal
from django.core.paginator import Paginator

from django.core.exceptions import ValidationError


def coupon_list(request):
    if not request.user.is_authenticated or not request.user.is_superuser:
        return redirect("admin_login")

    coupons_qs = Coupon.objects.all().order_by("-id")

    paginator = Paginator(coupons_qs, 5) 
    page_number = request.GET.get("page")
    coupons = paginator.get_page(page_number)

    return render(request, "admin_coupon_list.html", {
        "coupons": coupons
    })


def add_coupon(request):

    if not request.user.is_authenticated or not request.user.is_superuser:
        return redirect("admin_login")

    errors = {}

    if request.method == "POST":
        try:
            code = request.POST.get("code", "").strip().upper()
            discount_type = request.POST.get("discount_type")
            is_active = request.POST.get("is_active") == "on"

            if not code:
                errors["code"] = "Coupon code is required."
            elif Coupon.objects.filter(code=code).exists():
                errors["code"] = "Coupon code already exists."

            if discount_type not in ["flat", "percent"]:
                errors["discount_type"] = "Invalid discount type."

            try:
                discount_value = Decimal(request.POST.get("discount_value"))
                min_order_amount = Decimal(request.POST.get("min_order_amount"))
            except (InvalidOperation, TypeError):
                errors["discount_value"] = "Enter valid numeric values."

            try:
                usage_limit = int(request.POST.get("usage_limit"))
                max_uses_per_user = int(request.POST.get("max_uses_per_user", 1))
            except (ValueError, TypeError):
                errors["usage_limit"] = "Enter valid integer values."
            if "discount_value" not in errors and discount_value <= 0:
                errors["discount_value"] = "Discount value must be greater than zero."

            if "min_order_amount" not in errors and min_order_amount <= 0:
                errors["min_order_amount"] = "Minimum order amount must be greater than zero."

            if usage_limit < 1:
                errors["usage_limit"] = "Usage limit must be at least 1."

            if max_uses_per_user < 1:
                errors["max_uses_per_user"] = "Max uses per user must be at least 1."

            if max_uses_per_user > usage_limit:
                errors["max_uses_per_user"] = "Max uses per user cannot exceed usage limit."
            max_discount_amount = None
            if discount_type == "percent":
                if discount_value > 90:
                    errors["discount_value"] = "Percentage discount cannot exceed 90%."

                try:
                    max_discount_amount = Decimal(
                        request.POST.get("max_discount_amount")
                    )
                    if max_discount_amount <= 0:
                        errors["max_discount_amount"] = "Max discount amount must be greater than zero."
                except (InvalidOperation, TypeError):
                    errors["max_discount_amount"] = "Max discount amount is required for percentage coupons."

            valid_from_raw = request.POST.get("valid_from")
            valid_to_raw = request.POST.get("valid_to")

            if not valid_from_raw or not valid_to_raw:
                errors["date"] = "Valid From and Valid To are required."
            else:
                valid_from = timezone.make_aware(
                    timezone.datetime.fromisoformat(valid_from_raw)
                )
                valid_to = timezone.make_aware(
                    timezone.datetime.fromisoformat(valid_to_raw)
                )

                if valid_from >= valid_to:
                    errors["date"] = "Valid To must be after Valid From."

                if valid_to < timezone.now():
                    errors["date"] = "Valid To cannot be in the past."

            if errors:
                return render(
                    request,
                    "admin_add_coupon.html",
                    {"errors": errors}
                )

            Coupon.objects.create(
                code=code,
                discount_type=discount_type,
                discount_value=discount_value,
                min_order_amount=min_order_amount,
                usage_limit=usage_limit,
                max_uses_per_user=max_uses_per_user,
                is_active=is_active,
                valid_from=valid_from,
                valid_to=valid_to,
                max_discount_amount=max_discount_amount,
            )

            messages.success(request, "Coupon created successfully.")
            return redirect("coupon_list")

        except Exception:
            errors["general"] = "Something went wrong. Please check the inputs."

    return render(request, "admin_add_coupon.html", {"errors": errors})


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

from decimal import Decimal, InvalidOperation
from django.utils import timezone

def edit_coupon(request, coupon_id):

    if not request.user.is_authenticated or not request.user.is_superuser:
        return redirect("admin_login")

    coupon = get_object_or_404(Coupon, id=coupon_id)
    errors = {}

    if request.method == "POST":
        code = request.POST.get("code", "").strip().upper()
        discount_type = request.POST.get("discount_type")
        is_active = request.POST.get("is_active") == "on"

        if not code:
            errors["code"] = "Coupon code is required."
        elif Coupon.objects.filter(code=code).exclude(id=coupon.id).exists():
            errors["code"] = "Coupon code already exists."

        if discount_type not in ["flat", "percent"]:
            errors["discount_type"] = "Invalid discount type."

        try:
            discount_value = Decimal(request.POST.get("discount_value"))
            min_order_amount = Decimal(request.POST.get("min_order_amount"))
        except (InvalidOperation, TypeError):
            errors["discount_value"] = "Enter valid numeric values."

        try:
            usage_limit = int(request.POST.get("usage_limit"))
            max_uses_per_user = int(
                request.POST.get("max_uses_per_user", coupon.max_uses_per_user)
            )
        except (ValueError, TypeError):
            errors["usage_limit"] = "Enter valid integer values."

        if "discount_value" not in errors and discount_value <= 0:
            errors["discount_value"] = "Discount value must be greater than zero."

        if "min_order_amount" not in errors and min_order_amount <= 0:
            errors["min_order_amount"] = "Minimum order amount must be greater than zero."

        if usage_limit < 1:
            errors["usage_limit"] = "Usage limit must be at least 1."

        if max_uses_per_user < 1:
            errors["max_uses_per_user"] = "Max uses per user must be at least 1."

        if max_uses_per_user > usage_limit:
            errors["max_uses_per_user"] = "Max uses per user cannot exceed usage limit."

        max_discount_amount = None
        if discount_type == "percent":
            if discount_value > 90:
                errors["discount_value"] = "Percentage discount cannot exceed 90%."

            try:
                max_discount_amount = Decimal(
                    request.POST.get("max_discount_amount")
                )
                if max_discount_amount <= 0:
                    errors["max_discount_amount"] = "Max discount amount must be greater than zero."
            except (InvalidOperation, TypeError):
                errors["max_discount_amount"] = "Max discount amount is required."

        valid_from_raw = request.POST.get("valid_from")
        valid_to_raw = request.POST.get("valid_to")

        if not valid_from_raw or not valid_to_raw:
            errors["date"] = "Valid From and Valid To are required."
        else:
            valid_from = timezone.make_aware(
                timezone.datetime.fromisoformat(valid_from_raw)
            )
            valid_to = timezone.make_aware(
                timezone.datetime.fromisoformat(valid_to_raw)
            )

            if valid_from >= valid_to:
                errors["date"] = "Valid To must be after Valid From."

            if valid_to < timezone.now():
                errors["date"] = "Valid To cannot be in the past."

        if errors:
            return render(
                request,
                "admin_edit_coupon.html",
                {
                    "coupon": coupon,
                    "errors": errors,
                },
            )

        coupon.code = code
        coupon.discount_type = discount_type
        coupon.discount_value = discount_value
        coupon.min_order_amount = min_order_amount
        coupon.usage_limit = usage_limit
        coupon.max_uses_per_user = max_uses_per_user
        coupon.is_active = is_active
        coupon.valid_from = valid_from
        coupon.valid_to = valid_to
        coupon.max_discount_amount = max_discount_amount
        coupon.save()

        messages.success(request, "Coupon updated successfully.")
        return redirect("coupon_list")

    return render(
        request,
        "admin_edit_coupon.html",
        {
            "coupon": coupon,
            "errors": errors,
        },
    )
