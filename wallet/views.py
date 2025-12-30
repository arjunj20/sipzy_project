from django.shortcuts import render, redirect
from .models import Wallet, WalletTransaction



def wallet_page(request):

    wallet, _ = Wallet.objects.get_or_create(user=request.user)
    transactions = wallet.transactions.all()

    context = {
        "wallet": wallet,
        "transactions": transactions,
    }

    return render(request, "wallet_page.html", context)

