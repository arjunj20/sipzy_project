from django.db import models
from django.core.exceptions import ValidationError
from django.utils import timezone


class Coupon(models.Model):
    code = models.CharField(
        max_length=50,
        unique=True,
        help_text="Unique coupon code (stored in uppercase)"
    )

    discount_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Flat discount amount"
    )

    min_order_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Minimum order amount required to apply this coupon"
    )

    valid_from = models.DateTimeField()
    valid_to = models.DateTimeField()

    usage_limit = models.PositiveIntegerField(
        help_text="Maximum number of times this coupon can be used"
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
        """
        Model-level validations
        """
        if self.discount_amount <= 0:
            raise ValidationError("Discount amount must be greater than zero.")

        if self.min_order_amount <= 0:
            raise ValidationError("Minimum order amount must be greater than zero.")

        if self.discount_amount > self.min_order_amount:
            raise ValidationError(
                "Discount amount cannot be greater than minimum order amount."
            )

        if self.valid_from >= self.valid_to:
            raise ValidationError(
                "Valid To date must be greater than Valid From date."
            )

        if self.valid_to <= timezone.now():
            raise ValidationError("Coupon expiry date must be in the future.")

        if self.usage_limit < 1:
            raise ValidationError("Usage limit must be at least 1.")

    def save(self, *args, **kwargs):
        # Normalize coupon code
        self.code = self.code.upper().strip()

        # Run model validations
        self.full_clean()

        super().save(*args, **kwargs)

    def is_valid(self):
        """
        Check whether coupon can be applied
        """
        now = timezone.now()
        return (
            self.is_active
            and self.valid_from <= now <= self.valid_to
            and self.used_count < self.usage_limit
        )

    def __str__(self):
        return self.code
