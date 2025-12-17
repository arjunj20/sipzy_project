from django.urls import path
from . import views

urlpatterns = [

    path('admin-offers/', views.offer_list, name="offer_list"),
    path('admin-product-offer/', views.add_product_offer, name="add_product_offer"),


]