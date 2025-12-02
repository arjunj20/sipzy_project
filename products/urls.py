from django.urls import path
from . import views

urlpatterns = [

    path('user-product-list/', views.userproduct_list, name="userproduct_list"),
    path('user-product-details/<int:product_id>/', views.product_details, name="product_details"),
    path('add-to-cart/', views.add_to_cart, name="add_to_cart")
    
]
