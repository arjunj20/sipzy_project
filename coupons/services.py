from django.db import transaction
from .models import Coupon, CouponUsage

@transaction.atomic
def apply_coupon_for_user(user, coupon):
    # Lock coupon row
    coupon = Coupon.objects.select_for_update().get(id=coupon.id)

    if not coupon.is_valid():
        return False, "Coupon is invalid or expired"

    usage, _ = CouponUsage.objects.select_for_update().get_or_create(
        user=user,
        coupon=coupon
    )

    if usage.used_count >= coupon.max_uses_per_user:
        return False, "You have already used this coupon"

    if coupon.used_count >= coupon.usage_limit:
        return False, "Coupon usage limit reached"

    usage.used_count += 1
    usage.save()

    coupon.used_count += 1
    coupon.save()

    return True, "Coupon applied successfully"
