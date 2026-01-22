from decimal import Decimal
from .models import WalletTransaction, Wallet
from django.db import transaction

@transaction.atomic
def refund_to_wallet(user, amount, order, description):
    
    wallet, _ = Wallet.objects.select_for_update().get_or_create(user=user)
    amount = Decimal(amount)

    WalletTransaction.objects.create(
        wallet=wallet,
        transaction_type=WalletTransaction.CREDIT,
        amount=amount,
        order=order,
        description=description,
        status="completed"
    )

    wallet.balance += amount
    wallet.save()


@transaction.atomic
def debit_wallet(user, amount, order, description):
    wallet = Wallet.objects.select_for_update().get(user=user)
    amount = Decimal(amount)

    if amount <= 0:
        raise ValueError("Invalid debit amount")

    if wallet.balance < amount:
        raise ValueError("Insufficient wallet balance")

    WalletTransaction.objects.create(
        wallet=wallet,
        transaction_type=WalletTransaction.DEBIT,
        amount=amount,
        order=order,
        description=description,
        status="completed"
    )

    wallet.balance -= amount
    wallet.save()