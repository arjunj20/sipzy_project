from django.urls import path
from . import views


urlpatterns = [

    path('cart-page/', views.cart_page, name="cart_page"),
    path("update-cart-item/", views.update_cart_item, name="update_cart_item"),
    path("ajax-delete-item/", views.ajax_delete_item, name="ajax_delete_item"),
    path("checkout-page/", views.checkout_page, name="checkout_page"),
    path("place-order/", views.place_order, name="place_order"),
    path("order-placed/<int:order_id>/", views.order_placed, name="order_placed"),

    ]