from django.db import models
from django.core.exceptions import ValidationError
from django.utils import timezone
from decimal import Decimal
from django.conf import settings
from django.db import transaction


class Coupon(models.Model):

    DISCOUNT_TYPE_CHOICES = (
        ("flat", "Flat Amount"),
        ("percent", "Percentage"),
    )

    COUPON_SOURCE_CHOICES = (
        ("normal", "Normal"),
        ("referral", "Referral"),
    )

    coupon_source = models.CharField(
        max_length=20,
        choices=COUPON_SOURCE_CHOICES,
        default="normal"
    )

    code = models.CharField(
        max_length=50,
        unique=True,
        help_text="Unique coupon code (stored in uppercase)"
    )
    discount_type = models.CharField(max_length=10, choices=DISCOUNT_TYPE_CHOICES, default="flat")

    discount_value = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        help_text="Flat discount amount"
        )

    min_order_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Minimum order amount required to apply this coupon"
        )
    max_discount_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Max discount for percentage coupons"
    )

    valid_from = models.DateTimeField()
    valid_to = models.DateTimeField()

    usage_limit = models.PositiveIntegerField(
        help_text="Maximum number of times this coupon can be used"
    )
    
    max_uses_per_user = models.PositiveIntegerField(
        default=1,
        help_text="Maximum number of times a single user can use this coupon"
    )

    used_count = models.PositiveIntegerField(
        default=0,
        help_text="Number of times this coupon has been used"
    )

    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def clean(self):
            MIN_ORDER_LIMIT = Decimal("100.00")  
            if self.discount_value <= 0:
                raise ValidationError({"discount_value": "Discount value must be greater than zero."})

            if self.min_order_amount < MIN_ORDER_LIMIT:
                raise ValidationError({
                    "min_order_amount": f"Minimum order amount must be at least ₹{MIN_ORDER_LIMIT}."
                })

            if self.valid_from >= self.valid_to:
                raise ValidationError("Valid To must be after Valid From.")

            if self.max_uses_per_user > self.usage_limit:
                raise ValidationError({
                    "max_uses_per_user": "Max uses per user cannot exceed usage limit."
                })
            if self.discount_type == "flat":
                if self.discount_value >= self.min_order_amount:
                    raise ValidationError({
                        "discount_value": "Flat discount must be less than minimum order amount."
                    })
                self.max_discount_amount = None
            if self.discount_type == "percent":
                if self.discount_value > 90:
                    raise ValidationError({
                        "discount_value": "Percentage discount cannot exceed 90%."
                    })

                if not self.max_discount_amount or self.max_discount_amount <= 0:
                    raise ValidationError({
                        "max_discount_amount": "Max discount amount is required for percentage coupons."
                    })

                if self.max_discount_amount >= self.min_order_amount:
                    raise ValidationError({
                        "max_discount_amount": "Max discount must be less than minimum order amount."
                    })

        



    def save(self, *args, **kwargs):
        self.code = self.code.upper().strip()
        self.full_clean()
        super().save(*args, **kwargs)

    def is_valid(self):
        now = timezone.now()
        return (
            self.is_active
            and self.valid_from <= now <= self.valid_to
            and self.used_count < self.usage_limit
        )

    def __str__(self):
        return self.code
    
    def calculate_discount(self, order_total):

        if order_total < self.min_order_amount:
            return Decimal("0.00")
        if self.discount_type == "flat":
            return min(self.discount_value, order_total)
        
        discount = (self.discount_value / Decimal("100")) * order_total

        if self.max_discount_amount:
            discount = min(self.max_discount_amount, discount)

        return discount
    

class CouponUsage(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    coupon = models.ForeignKey(Coupon, on_delete=models.CASCADE)
    used_count = models.PositiveIntegerField(default=0)

    class Meta:
        unique_together = ('user', 'coupon')

    def __str__(self):
        return f"{self.user} - {self.coupon} ({self.used_count})"


