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

    
]