from django.urls import path
from . import views


urlpatterns = [
    path("order-list/", views.order_list, name="order_list"),
    path('order/<uuid:uuid>/', views.order_detail, name='order_detail'),
    path('order-invoice/<int:order_id>/', views.order_invoice, name="order_invoice"),
        
        
    path("cancel/<uuid:uuid>/", views.cancel_item, name="cancel_item"),
    path("return-item/<uuid:uuid>/", views.submit_return_request, name="submit_return_request"),




]   