from django.urls import path
from . import views

urlpatterns = [

    path('admin-offers/', views.offer_list, name="offer_list"),
    path('admin-product-offer/', views.add_product_offer, name="add_product_offer"),
    path('edit-product-offer/<uuid:uuid>/', views.edit_product_offer, name="edit_product_offer"),
    path('deactivate-product-offer/<uuid:uuid>/', views.deactivate_product_offer, name="deactivate_product_offer"),
    path('activate-product-offer/<uuid:uuid>/', views.activate_product_offer, name="activate_product_offer"),
    path('category-offer-list/', views.category_offer_list, name="category_offer_list"),
    path('category-add-offer/', views.category_add_offer, name="category_add_offer"),
    path('category-edit-offer/<uuid:uuid>/', views.edit_category_offer, name="edit_category_offer"),
    path("category-offer/deactivate/<uuid:uuid>/", views.deactivate_category_offer, name="deactivate_category_offer"),
    path("category-offer/activate/<uuid:uuid>/", views.activate_category_offer, name="activate_category_offer"),


]