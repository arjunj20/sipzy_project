from django.db import models
from authenticate.models import CustomUser
from orders.models import Order

class Wallet(models.Model):
    user = models.OneToOneField(
        CustomUser,
        on_delete=models.CASCADE,
        related_name="wallet"
    )
    balance = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.email} Wallet"


class WalletTransaction(models.Model):
    CREDIT = "credit"
    DEBIT = "debit"

    TRANSACTION_TYPE = (
        (CREDIT, "Credit"),
        (DEBIT, "Debit"),
    )

    wallet = models.ForeignKey(
        Wallet,
        on_delete=models.CASCADE,
        related_name="transactions"
    )
    transaction_type = models.CharField(
        max_length=10,
        choices=TRANSACTION_TYPE
    )
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    order = models.ForeignKey(
        Order,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    status = models.CharField(
        max_length=20,
        choices=(("pending", "Pending"), ("completed", "Completed")),
        default="completed"
    )

    description = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.transaction_type.upper()} - {self.amount}"
