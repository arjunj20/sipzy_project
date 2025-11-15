from django.urls import path
from . import views


urlpatterns = [

    path('user-signup/', views.user_signup, name="user_signup"),
    path('user-signupotp/', views.user_signupotp, name="user_signupotp"),
    path('user-login/', views.user_login, name="user_login"),
    path('user-resend/', views.resend_otp, name="resend_otp"),
    path('landing-page/', views.landing_page, name="landing_page"),
    path('home-page/', views.user_homepage, name="user_homepage"),
    path('user-logout/', views.user_logout, name="user_logout"),
    path('forgot-password/', views.forgot_password, name="forgot_password"),
    path('forgot-password-otp/', views.forgot_password_otp, name="forgot_password_otp"),
    path('reset-password/', views.reset_password, name="reset_password"),
    path("resend-forgot-otp/", views.resend_forgot_otp, name="resend_forgot_otp"),

    
]