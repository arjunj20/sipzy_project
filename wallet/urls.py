from django.urls import path
from . import views

urlpatterns = [

    path("wallet-page/", views.wallet_page, name="wallet_page")
]