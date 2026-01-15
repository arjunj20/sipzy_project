from django.shortcuts import render, redirect
from .models import Wallet, WalletTransaction



from django.shortcuts import render, redirect
from django.core.paginator import Paginator 

def wallet_page(request):
    if not request.user.is_authenticated or request.user.is_superuser:
        return redirect("user_login")

    wallet, _ = Wallet.objects.get_or_create(user=request.user)
    
    transaction_list = wallet.transactions.all().order_by('-created_at')

    paginator = Paginator(transaction_list, 10) 
    
    page_number = request.GET.get('page')
    
    transactions = paginator.get_page(page_number)

    context = {
        "wallet": wallet,
        "transactions": transactions, 
    }

    return render(request, "wallet_page.html", context)

