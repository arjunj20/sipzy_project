from django.db import models
from authenticate.models import CustomUser, Address
from products.models import Products,ProductVariants
from decimal import Decimal
import uuid

class Order(models.Model):
    PAYMENT_CHOICES = (
        ("COD", "Cash on Delivery"),
        ("Razorpay", "Razorpay")

    )
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)

    user = models.ForeignKey(CustomUser, related_name="orders", on_delete=models.CASCADE)
    address = models.ForeignKey(Address, on_delete=models.SET_NULL, null=True)

    payment_method = models.CharField(max_length=20, choices=PAYMENT_CHOICES)
    payment_status = models.CharField(max_length=20, default="not paid")

    subtotal = models.DecimalField(max_digits=10, decimal_places=2)
    tax = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    shipping_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    discount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=10, decimal_places=2)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    order_number = models.CharField(max_length=20, unique=True, blank=True, null=True)

    def __str__(self):
        return f"Order {self.id} - {self.user.fullname}"
    





    def recalculate_totals(self):
        active_items = self.items.exclude(
            status__in=["cancelled", "returned"]
        )

        self.subtotal = sum(
            item.price * item.quantity
            for item in active_items
        )

        TAX_RATE = Decimal("0.18")

        # 🔹 Extract tax from inclusive price (INFO ONLY)
        self.tax = (self.subtotal * TAX_RATE / (1 + TAX_RATE)).quantize(Decimal("0.01"))

        # 🔹 DO NOT add tax again
        self.total = (
            self.subtotal
            + self.shipping_fee
            - self.discount
        )

        self.save(update_fields=["subtotal", "tax", "total"])



    def save(self, *args, **kwargs):
        if not self.order_number:
            super().save(*args, **kwargs)   # get ID
            self.order_number = f"sz{1000 + self.id}"
            super().save(update_fields=["order_number"])
        else:
            super().save(*args, **kwargs)



           
class OrderItem(models.Model):
    ITEM_STATUS_CHOICES = (
        ("pending", "Pending"),
        ("processing", "Processing"),
        ("shipped", "Shipped"),
        ("delivered", "Delivered"),

        ("return_requested", "Return Requested"),
        ("returned", "Returned"),
        ("cancelled", "Cancelled"),
    )

    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)

    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(Products, on_delete=models.SET_NULL, null=True)
    variant = models.ForeignKey(ProductVariants, on_delete=models.SET_NULL, null=True)
    cancel_reason = models.TextField(blank=True, null=True)

    quantity = models.PositiveIntegerField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, choices=ITEM_STATUS_CHOICES, default="pending")

    sub_order_id = models.CharField(max_length=50, blank=True, unique=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        is_new = self.pk is None

        super().save(*args, **kwargs)

        if is_new and not self.sub_order_id:
            OrderItem.objects.filter(pk=self.pk).update(
                sub_order_id=f"{self.order.order_number}-{self.id}"
            )


    def __str__(self):
        return f"{self.product.name} ({self.quantity})"


class ReturnRequest(models.Model):
    RETURN_STATUS_CHOICES = (
        ("pending", "Pending"),
        ("approved", "Approved"),
        ("rejected", "Rejected"),
        ("refunded", "Refunded"),
    )

    order_item = models.OneToOneField(
        OrderItem, on_delete=models.CASCADE, related_name="return_request"
    )

    reason = models.TextField()
    status = models.CharField(max_length=20, choices=RETURN_STATUS_CHOICES, default="pending")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

