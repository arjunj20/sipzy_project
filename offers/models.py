from django.db import models
from products.models import Products,Category
from django.core.exceptions import ValidationError
import uuid
from django.utils import timezone



class ProductOffer(models.Model):

    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    product = models.ForeignKey(Products, on_delete=models.CASCADE, related_name="product_offers")
    offer_name = models.CharField(max_length=100)
    discount_percent = models.PositiveSmallIntegerField( help_text="Discount percentage (0–90)")
    start_date = models.DateField()
    end_date = models.DateField()

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["product"],
                condition=models.Q(is_active=True),
                name="unique_active_product_offer"
            )
        ]

    @property
    def is_expired(self):
        return timezone.now().date() > self.end_date


    def clean(self):
        if self.discount_percent>90:
            raise ValidationError("Discount cannot exceed 90%")
        if self.start_date>=self.end_date:
            raise ValidationError("End date must be after Start date")
    

    def __str__(self):
        return f"{self.offer_name} - {self.discount_percent}%"


class CategoryOffer(models.Model):
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)

    category = models.ForeignKey(
        Category,
        on_delete=models.CASCADE,
        related_name="category_offers"
    )

    offer_name = models.CharField(max_length=100)
    discount_percent = models.PositiveSmallIntegerField(
        help_text="Discount percentage (1–90)"
    )

    start_date = models.DateField()
    end_date = models.DateField()

    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["category"],
                condition=models.Q(is_active=True),
                name="unique_active_category_offer"
            )
        ]

    def clean(self):
        if self.discount_percent > 90:
            raise ValidationError("Discount cannot exceed 90%")
        if self.start_date >= self.end_date:
            raise ValidationError("End date must be after start date")

    @property
    def is_expired(self):
        return timezone.now().date() > self.end_date

    def __str__(self):
        return f"{self.offer_name} - {self.discount_percent}%"
