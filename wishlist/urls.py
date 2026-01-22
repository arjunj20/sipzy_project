from django.urls import path
from . import views

urlpatterns = [
    path("", views.wishlist_page, name="wishlist"),
    path("add/<uuid:product_uuid>/", views.add_to_wishlist, name="add_to_wishlist"),
    path("remove/<uuid:product_uuid>/", views.remove_from_wishlist, name="remove_from_wishlist"),
    path("move-to-cart/<uuid:product_uuid>/", views.move_to_cart, name="move_to_cart"),
]
