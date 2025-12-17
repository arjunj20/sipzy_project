from django.db import models
from products.models import Products
from django.core.exceptions import ValidationError



class ProductOffer(models.Model):
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
    def clean(self):
        if self.discount_percent>90:
            raise ValidationError("Discount cannot exceed 90%")
        if self.start_date>=self.end_date:
            raise ValidationError("End date must be after Start date")
        

    def __str__(self):
        return f"{self.offer_name} - {self.discount_percent}%"
