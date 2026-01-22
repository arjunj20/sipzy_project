from django.urls import path
from . import views

urlpatterns = [

    path("list/", views.coupon_list, name="coupon_list"),
    path("add/", views.add_coupon, name="add_coupon"),
    path("delete/<int:coupon_id>/", views.delete_coupon, name="delete_coupon"),
    path("coupons/<int:coupon_id>/edit/", views.edit_coupon, name="edit_coupon"),



]