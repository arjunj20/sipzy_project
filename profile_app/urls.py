from django.urls import path
from . import views

urlpatterns = [
    path("user-profile/", views.user_profile, name="user_profile"),
    path("profile-edit/", views.edit_profile, name="edit_profile"),

    path("change-email/", views.change_email, name="change_email"),
    path("email-otp/", views.email_otp, name="email_otp"),

    path("change-password/", views.change_password, name="change_password"),
    path("address/edit/<uuid:uuid>/", views.edit_addresses, name="edit_addresses"),

    path("address-add/", views.add_addresses, name="add_addresses"),
    path("address-delete/<uuid:uuid>/", views.delete_address, name="delete_address"),
    path("resend-otp/", views.resend_email_otp, name="resend_email_otp"),


]
