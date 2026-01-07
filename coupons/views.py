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
            discount_value = Decimal(request.POST.get("discount_value"))
            min_order_amount = Decimal(request.POST.get("min_order_amount"))
            usage_limit = int(request.POST.get("usage_limit"))
            max_uses_per_user = int(request.POST.get("max_uses_per_user", 1))
            is_active = request.POST.get("is_active") == "on"

            valid_from_raw = request.POST.get("valid_from")
            valid_to_raw = request.POST.get("valid_to")
            if not valid_from_raw or not valid_to_raw:
                raise ValidationError({"date": "Both Valid From and Valid To are required."})
            valid_from = timezone.make_aware(timezone.datetime.fromisoformat(valid_from_raw))
            valid_to = timezone.make_aware(timezone.datetime.fromisoformat(valid_to_raw))

            max_discount_amount = None
            if discount_type == "percent":
                max_discount_amount = Decimal(request.POST.get("max_discount_amount"))

            if max_uses_per_user < 1:
                raise ValidationError({
                    "max_uses_per_user": "Max uses per user must be at least 1."
                })

            if Coupon.objects.filter(code=code).exists():
                raise ValidationError({"code": "Coupon code already exists."})

            if discount_type not in ["flat", "percent"]:
                raise ValidationError({"discount_type": "Invalid discount type."})

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
                max_discount_amount=max_discount_amount
            )
            messages.success(request, "Coupon created successfully..")
            return redirect("coupon_list")
        except ValidationError as e:
            errors = e.message_dict

        except Exception:
            errors["general"] = "Invalid input data"
            
            

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


def edit_coupon(request, coupon_id):
    if not request.user.is_authenticated or not request.user.is_superuser:
        return redirect("admin_login")

    coupon = get_object_or_404(Coupon, id=coupon_id)
    errors = {}

    if request.method == "POST":
        try:
            code = request.POST.get("code", "").strip().upper()
            discount_type = request.POST.get("discount_type")
            discount_value = Decimal(request.POST.get("discount_value"))
            min_order_amount = Decimal(request.POST.get("min_order_amount"))
            usage_limit = int(request.POST.get("usage_limit"))
            max_uses_per_user = int(
                request.POST.get("max_uses_per_user", coupon.max_uses_per_user)
            )

            is_active = request.POST.get("is_active") == "on"

            valid_from_raw = request.POST.get("valid_from")
            valid_to_raw = request.POST.get("valid_to")

            if not valid_from_raw or not valid_to_raw:
                raise ValidationError({"date": "Both Valid From and Valid To are required."})
            if max_uses_per_user < 1:
                raise ValidationError({
                    "max_uses_per_user": "Max uses per user must be at least 1."
                })


            valid_from = timezone.make_aware(
                timezone.datetime.fromisoformat(valid_from_raw)
            )
            valid_to = timezone.make_aware(
                timezone.datetime.fromisoformat(valid_to_raw)
            )

            max_discount_amount = None
            if discount_type == "percent":
                max_discount_amount = Decimal(request.POST.get("max_discount_amount"))

            # 🔥 IMPORTANT: exclude current coupon when checking code
            if Coupon.objects.filter(code=code).exclude(id=coupon.id).exists():
                raise ValidationError({"code": "Coupon code already exists."})

            if discount_type not in ["flat", "percent"]:
                raise ValidationError({"discount_type": "Invalid discount type."})

            # ✅ Update coupon
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

        except ValidationError as e:
            errors = e.message_dict

        except Exception:
            errors["general"] = "Invalid input data"

    return render(
        request,
        "admin_edit_coupon.html",
        {
            "coupon": coupon,
            "errors": errors
        }
    )

