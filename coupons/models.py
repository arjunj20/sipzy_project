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
        if self.discount_value <= 0:
            raise ValidationError("Discount value must be greater than zero.")

        if self.discount_type == "percent":
            if self.discount_value > 100:
                raise ValidationError("Percentage discount cannot exceed 100%.")
            if not self.max_discount_amount:
                raise ValidationError("Max discount amount is required for percentage coupons.")
        else:
            self.max_discount_amount = None

        if self.min_order_amount <= 0:
            raise ValidationError("Minimum order amount must be greater than zero.")

        if self.valid_from >= self.valid_to:
            raise ValidationError("Invalid validity dates.")

        



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


