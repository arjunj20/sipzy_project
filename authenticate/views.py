from django.shortcuts import render, redirect
from .models import CustomUser

from django.views.decorators.cache import never_cache
import random
from django.core.mail import send_mail
from django.utils import timezone
from django.utils.dateparse import parse_datetime
import datetime
from django.contrib.auth import authenticate, login, logout
from allauth.socialaccount.models import SocialAccount
from django.contrib.auth.hashers import make_password
from django.contrib.auth.hashers import make_password





@never_cache
def user_signup(request):

    if request.user.is_authenticated and not request.user.is_superuser:
        return redirect("user_homepage")
    
    errors={}

    if request.method == 'POST':
        fullname = request.POST.get("fullname")
        email = request.POST.get("email")
        password = request.POST.get("password")
        confirmpassword =request.POST.get("confirm_password")



        if not fullname:
            errors["fullname"] = "fullname is required"
        
        if not email:
            errors["email"] = "email is required"
        if not password:
            errors["password"] = "password is required"
        elif len(password) < 6:
            errors["password_length"] = "password must be atleast 6 characters"
        if password != confirmpassword:
            errors["password_match"] = "passwords do not match"
        if email and CustomUser.objects.filter(email=email).exists():
            errors["email_exist"] = "email is already taken.."
        
        if fullname and CustomUser.objects.filter(fullname=fullname).exists():
            errors["fullname_exist"] = "name is already taken"

        if errors:
            return render(request, "user_signup.html", {"errors": errors})
        

        otp = random.randint(100000, 999999)
        
        request.session["signup_data"] = {
            'fullname': fullname,
            'email': email,
            "password": make_password(password),
            'otp': otp,
            "otp_time": timezone.now().isoformat()

        }

        send_mail(
            subject="Sipzy - Email Verification OTP",
            message=f"Hello {fullname},\n\nYour verification OTP is {otp}. It will expire in 5 minutes.\n\nThank you!",
            from_email="sipzy505@gmail.com",
            recipient_list=[email],
            fail_silently=False,
        )

        return redirect("user_signupotp")

    return render(request, "user_signup.html")

@never_cache
def user_signupotp(request):
    if request.user.is_authenticated and not request.user.is_superuser:
        return redirect("user_homepage")
    error = {}
    signup_data = request.session.get("signup_data")
    if not signup_data:
        return redirect("user_signup")
        
    correct_otp = str(signup_data["otp"])

    otp_time = parse_datetime(signup_data["otp_time"])
    otp_time = otp_time.astimezone(timezone.get_current_timezone())
    now = timezone.now()
    elapsed = (now - otp_time).total_seconds()
    total_allowed = 100  
    remaining_time = max(0, int(total_allowed - elapsed))

    if request.method == 'POST':
        otp1 = request.POST.get('otp1')
        otp2 = request.POST.get('otp2')
        otp3 = request.POST.get('otp3')
        otp4 = request.POST.get('otp4')
        otp5 = request.POST.get('otp5')
        otp6 = request.POST.get('otp6')
        
        enteredotp = otp1 + otp2 + otp3 + otp4 + otp5 + otp6       
        if remaining_time <= 0:
            return render(request, "user_signupotp.html", {
                "error": {"resend_error": "OTP expired. Please resend OTP."}, "remaining_time":0
            })
    
        if enteredotp != correct_otp:
            return render(request, "user_signupotp.html", {
                "error": {"incorrect_otp": "Incorrect OTP. Try again."}
            })        
        
        if error:
            return render(request, "user_signupotp.html", {"error": error})
          
        user = CustomUser.objects.create_user(fullname=signup_data["fullname"], email=signup_data["email"], password=signup_data["password"])
        user.save()
        del request.session["signup_data"]
        return redirect("user_login")

    return render(request, "user_signupotp.html", {"remaining_time": remaining_time})

@never_cache
def resend_otp(request):

    signup_data = request.session.get("signup_data")

    if not signup_data:
        return redirect("user_signup")
    
    new_otp = random.randint(100000, 999999)

    signup_data["otp"] = new_otp
    signup_data["otp_time"] = timezone.now().isoformat()

    request.session["signup_data"] = signup_data

    send_mail(
        
        subject="Sipzy - New OTP Verification Code",
        message=f"Hello {signup_data['fullname']},\n\nYour new OTP is {new_otp}.",
        from_email="sipzy505@gmail.com",
        recipient_list=[signup_data["email"]],
        fail_silently=False,

    )
    return redirect("user_signupotp")

@never_cache
def user_homepage(request):

    if not request.user.is_authenticated or request.user.is_superuser:
        return redirect("landing_page")
    user = request.user
    fullname = user.fullname

    if not fullname:
        google_account = SocialAccount.objects.filter(user=user, provider="google").first()
        if google_account:
            fullname = google_account.extra_data.get("name") 

    return render(request, "user_home.html", {"fullname": fullname})

@never_cache
def landing_page(request):
    if request.user.is_authenticated and not request.user.is_superuser:
        return redirect("user_homepage")
  
    return render(request, "landing.html")

@never_cache
def user_login(request):
    

    if request.user.is_authenticated and not request.user.is_superuser:
        return redirect("user_homepage")
    errors = {}

    if request.method == 'POST':
        email = request.POST.get("email")
        password = request.POST.get("password")
        if not email:
            errors["email"] = "Email must be filled"

        if not password:
            errors["password"] = "Password must be filled"
        if errors:
            return render(request, "user_login.html", {"errors": errors})
        
        user = authenticate(request, email=email, password=password)

        if user is None:
            errors["invalid"] = "Invalid email or password!"
            return render(request, "user_login.html", {"errors": errors})
        if not user.is_active:
            errors["inactive"] = "User account is inactive"
            return render(request, "user_login.html", {"errors": errors})
        
        login(request, user)
        request.session["is_loggedin"] = True
        user.is_loggedin = True
        user.save()
        return redirect("user_homepage")

    return render(request, "user_login.html")

@never_cache
def user_logout(request):
    user = request.user
    if request.user.is_authenticated and not request.user.is_superuser:
        user.is_loggedin = False
        user.save()
        logout(request)
    return redirect("user_homepage")

@never_cache
def forgot_password(request):

    errors = {}

    if request.method == "POST":
        email = request.POST.get("email")

        if not email:
            errors["email"] = "email is required"
        elif not CustomUser.objects.filter(email=email).exists():
            errors["email"] = "Email is not registered"
        if errors:
            return render(request, "forgot_password.html", {"errors": errors})
        
        otp = str(random.randint(100000, 999999))

        request.session["forgot_email"] = email
        request.session["forgot_otp"] = otp
        request.session["forgot_otp_time"] = timezone.now().isoformat()

        send_mail(
            subject="Sipzy - Password Reset OTP",
            message=f"Hello,\n\nYour OTP for resetting your Sipzy password is {otp}. "
                    f"It will expire in 5 minutes.\n\nThank you!",
            from_email="sipzy505@gmail.com",
            recipient_list=[email],
            fail_silently=False,
        )
        return redirect("forgot_password_otp")

    return render(request, "forgot_password.html")


@never_cache
def forgot_password_otp(request):
    error = ""

    email = request.session.get("forgot_email")
    session_otp = request.session.get("forgot_otp")
    otp_time = request.session.get("forgot_otp_time")

    if not email or not session_otp:
        return redirect("forgot_password")

    if request.method == "POST":
        otp = (
            request.POST.get("otp1")
            + request.POST.get("otp2")
            + request.POST.get("otp3")
            + request.POST.get("otp4")
            + request.POST.get("otp5")
            + request.POST.get("otp6")
        )

        otp_datetime = parse_datetime(otp_time)
        now = timezone.now()
        diff = (now - otp_datetime).total_seconds()

        if diff > 300: 
            error = "OTP expired. Request a new one."
        elif otp != session_otp:
            error = "Incorrect OTP"
        else:
            request.session["forgot_verified"] = True
            return redirect("reset_password")
    return render(request, "forgot_password_otp.html", {"error": error})


@never_cache
def reset_password(request):
    email = request.session.get("forgot_email")
    verified = request.session.get("forgot_verified")

    if not email or not verified:
        return redirect("forgot_password")

    errors = {}

    if request.method == "POST":
        password = request.POST.get("password")
        confirm_password = request.POST.get("confirm_password")

        if not password:
            errors["password"] = "Password is required"

        elif len(password) < 6:
            errors["password"] = "Password must be at least 6 characters long"


        if password != confirm_password:
            errors["confirm_password"] = "Passwords do not match"

        if not errors:
            user = CustomUser.objects.get(email=email)
            user.password = make_password(password)
            user.save()

            request.session.pop("forgot_email", None)
            request.session.pop("forgot_otp", None)
            request.session.pop("forgot_otp_time", None)
            request.session.pop("forgot_verified", None)

            return redirect("user_login")
    return render(request, "reset_password.html", {"errors": errors})

@never_cache
def resend_forgot_otp(request):
    email = request.session.get("forgot_email")

    if not email:
        return redirect("forgot_password")

    otp = str(random.randint(100000, 999999))

    request.session["forgot_otp"] = otp
    request.session["forgot_otp_time"] = timezone.now().isoformat()

    send_mail(
        subject="Sipzy - Password Reset OTP (Resent)",
        message=f"Hello,\n\nYour new OTP for resetting your Sipzy password is {otp}. "
                f"It will expire in 5 minutes.\n\nThank you!",
        from_email="sipzy505@gmail.com",
        recipient_list=[email],
        fail_silently=False,
    )

    return redirect("forgot_password_otp")






