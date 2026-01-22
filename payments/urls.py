from django.urls import path
from . import views


urlpatterns = [


    path("start/<uuid:uuid>/", views.start_payment, name="start_payment"), 
    path("verify/", views.verify_payment, name="verify_payment"),
    path("success/<uuid:uuid>/", views.payment_success, name="payment_success"),
    path("failure/<uuid:uuid>/", views.payment_failure, name="payment_failure"),
            


]