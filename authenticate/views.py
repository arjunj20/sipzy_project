from django.shortcuts import render, redirect
from .models import CustomUser
from products.models import Products,ProductVariants

from django.views.decorators.cache import never_cache
import random
from django.db.models import Count
from django.core.mail import send_mail
from django.utils import timezone
from django.utils.dateparse import parse_datetime
import datetime
from django.contrib.auth import authenticate, login, logout
from allauth.socialaccount.models import SocialAccount
from django.contrib.auth.hashers import make_password
from django.contrib.auth.hashers import make_password
from django.shortcuts import render, redirect
from django.db.models import Count
from allauth.socialaccount.models import SocialAccount
from django.views.decorators.cache import never_cache
from django.contrib import messages


from django.shortcuts import render, redirect
from django.views.decorators.cache import never_cache
from django.utils import timezone
from django.core.mail import send_mail
import random

from referal.models import Referral
from authenticate.models import CustomUser   # adjust import if needed
from coupons.models import Coupon

import random
import re
from django.utils import timezone
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
from django.views.decorators.cache import never_cache

FULLNAME_REGEX = re.compile(r"^[A-Za-z][A-Za-z .]{1,48}[A-Za-z]$")
PASSWORD_REGEX = re.compile(r"^(?=.*[A-Za-z])(?=.*\d)[A-Za-z\d@#$!%*?&]{8,}$")

@never_cache
def user_signup(request):

    if request.user.is_authenticated and not request.user.is_superuser:
        return redirect("user_homepage")

    errors = {}
    referral_token = request.GET.get("ref")
    if referral_token:
        request.session["referral_token"] = referral_token
    data_form = request.POST.copy()

    if request.method == "POST":

        fullname = request.POST.get("fullname", "").strip()
        email = request.POST.get("email", "").strip()
        password = request.POST.get("password")
        confirmpassword = request.POST.get("confirm_password")

        if not fullname:
            errors["fullname"] = "Full name is required."
        elif not FULLNAME_REGEX.match(fullname):
            errors["fullname"] = "Name can contain only letters, spaces, and dot (.)."
        elif CustomUser.objects.filter(fullname=fullname).exists():
            errors["fullname"] = "Full name already exists."

        if not email:
            errors["email"] = "Email is required."
        else:
            try:
                validate_email(email)
            except ValidationError:
                errors["email"] = "Enter a valid email address."

            if CustomUser.objects.filter(email=email).exists():
                errors["email"] = "Email is already registered."

  
        if not password:
            errors["password"] = "Password is required."
        elif not PASSWORD_REGEX.match(password):
            errors["password"] = (
                "Password must be at least 8 characters long "
                "and include letters and numbers."
            )

        if password and confirmpassword and password != confirmpassword:
            errors["confirm_password"] = "Passwords do not match."

        if errors:
            return render(request, "user_signup.html", {"errors": errors, "data_form": data_form})

        try:
            otp = random.randint(100000, 999999)

            request.session["signup_data"] = {
                "fullname": fullname,
                "email": email,
                "password": password,
                "otp": otp,
                "otp_time": timezone.now().isoformat(),
                "referral_token": request.session.get("referral_token"),
            }

            send_mail(
                subject="Sipzy - Email Verification OTP",
                message=(
                    f"Hello {fullname},\n\n"
                    f"Your OTP is {otp}.\n\n"
                    "This OTP is valid for 1.40 minutes.\n\n"
                    "Sipzy Team"
                ),
                from_email="sipzy505@gmail.com",
                recipient_list=[email],
                fail_silently=False,
            )

            return redirect("user_signupotp")

        except Exception:
            errors["general"] = "Something went wrong. Please try again."
            return render(request, "user_signup.html", {"errors": errors, "data_form": data_form})

    return render(request, "user_signup.html", {"data_form": data_form})


import uuid
from datetime import timedelta

@never_cache
def user_signupotp(request):

    if request.user.is_authenticated and not request.user.is_superuser:
        return redirect("user_homepage")

    errors = {}
    signup_data = request.session.get("signup_data")
    if not signup_data:
        messages.error(request, "Session expired. Please sign up again.")
        return redirect("user_signup")

    correct_otp = str(signup_data["otp"])

    try:
        otp_time = parse_datetime(signup_data["otp_time"])
        otp_time = otp_time.astimezone(timezone.get_current_timezone())
    except Exception as e:
        print("OTP TIME ERROR:", e)
        messages.error(request, "OTP error. Please try again.")
        return redirect("user_signup")

    now = timezone.now()
    elapsed = (now - otp_time).total_seconds()
    allowed_time = 100
    remaining_time = max(0, int(allowed_time - elapsed))

    if request.method == 'POST':
        otp_digits = [request.POST.get(f'otp{i}', '') for i in range(1, 7)]

        if any(d.strip() == "" for d in otp_digits):
            errors["otp_empty"] = "Please enter all 6 digits of the OTP."
        if not all(d.isdigit() for d in otp_digits):
            errors["otp_numeric"] = "OTP must contain only numbers."

        entered_otp = "".join(otp_digits)

        if remaining_time <= 0:
            errors["otp_expired"] = "OTP expired. Please resend OTP."

        if entered_otp != correct_otp:
            errors["incorrect_otp"] = "Incorrect OTP. Try again."

        if errors:
            return render(request, "user_signupotp.html", {
                "error": errors,
                "remaining_time": remaining_time
            })

        try:
            user = CustomUser.objects.create_user(
                fullname=signup_data["fullname"],
                email=signup_data["email"],
                password=signup_data["password"]
            )
            user.save()

            referral_token = signup_data.get("referral_token")

            if referral_token:
                try:
                    referral = Referral.objects.get(
                        token=referral_token,
                        is_used=False
                    )

                    if referral.referrer != user:
                        referral.is_used = True
                        referral.referred_user = user
                        referral.save()

                        Coupon.objects.create(
                            code="REF" + uuid.uuid4().hex[:8],
                            coupon_source="referral",
                            discount_type="percent",
                            discount_value=10,
                            min_order_amount=500,
                            max_discount_amount=200,
                            valid_from=timezone.now(),
                            valid_to=timezone.now() + timedelta(days=30),
                            usage_limit=1,
                            max_uses_per_user=1,
                            is_active=True
                        )

                except Referral.DoesNotExist:
                    pass

            del request.session["signup_data"]
            request.session.pop("referral_token", None)

            messages.success(request, "Account created successfully!")
            return redirect("user_login")

        except Exception as e:
            print("USER CREATION ERROR:", e)
            errors["server_error"] = "Something went wrong. Please try again."
            return render(request, "user_signupotp.html", {
                "error": errors,
                "remaining_time": remaining_time
            })

    return render(request, "user_signupotp.html", {
        "remaining_time": remaining_time
    })


@never_cache
def resend_otp(request):

    if request.user.is_authenticated and not request.user.is_superuser:
        return redirect("user_homepage")

    signup_data = request.session.get("signup_data")

    if not signup_data:
        return redirect("user_signup")
    
    new_otp = random.randint(100000, 999999)

    signup_data["otp"] = new_otp
    signup_data["otp_time"] = timezone.now().isoformat()

    request.session["signup_data"] = signup_data

    send_mail(
        
        subject="Sipzy - New OTP Verification Code",
        message=(
        f"Hello {signup_data['fullname']},\n\n"
        "You requested a new OTP to verify your email address "
        "for creating your Sipzy account.\n\n"
        f"Your new One-Time Password (OTP) is: {new_otp}\n\n"
        "⏰ This OTP is valid for 1.36 minutes only.\n\n"
        "If you did not request this OTP, please ignore this email.\n\n"
        "Thank you,\n"
        "Sipzy Team"
        ),
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

    products = (
        Products.objects
        .annotate(variant_count=Count("variants"))
        .filter(
            is_active=True,
            category__is_active=True,
            brand__is_active=True,
            variant_count__gte=1
        )
        .select_related("brand", "category")
    )

    for product in products:
        product.default_variant = product.variants.order_by("-price").first()

    if not fullname:
        google_account = SocialAccount.objects.filter(user=user, provider="google").first()
        if google_account:
            fullname = google_account.extra_data.get("name")

    return render(
        request,
        "user_home.html",
        {
            "fullname": fullname,
            "featured_products": products,
            "trending_products": products,
            "handpicked_products": products,
            
        }
    )


@never_cache
def landing_page(request):
    if request.user.is_authenticated and not request.user.is_superuser:
        return redirect("user_homepage")
    
    products = (
        Products.objects
        .annotate(variant_count=Count("variants"))
        .filter(
            is_active=True,
            category__is_active=True,
            brand__is_active=True,
            variant_count__gte=1
        )
        .select_related("brand", "category")
    )
    for product in products:
        product.default_variant = product.variants.order_by("-price").first()
        
    return render(request, "landing.html",{

            "featured_products": products,
            "trending_products": products,
            "handpicked_products": products,

    })


@never_cache
def user_login(request):

    if request.user.is_authenticated and not request.user.is_superuser:
        return redirect("user_homepage")

    errors = {}
    data_form = {} 

    if request.method == "POST":

        email = (request.POST.get("email") or "").strip()
        password = request.POST.get("password") or ""

        data_form = {
            "email": email  
        }

        if not email:
            errors["email"] = "Email is required."
        else:
            try:
                validate_email(email)
            except ValidationError:
                errors["email"] = "Enter a valid email address."

        if not password:
            errors["password"] = "Password is required."
        elif len(password) > 128:
            errors["password"] = "Invalid password."

        if errors:
            return render(request, "user_login.html", {"errors": errors, "data_form": data_form})

        user = authenticate(request, email=email, password=password)

        if user is None:
            errors["invalid"] = "Invalid email or password."
            return render(request, "user_login.html", {"errors": errors, "data_form": data_form})

        if not user.is_active:
            errors["inactive"] = "User account is inactive. Contact support."
            return render(request, "user_login.html", {"errors": errors, "data_form": data_form})

        login(request, user)
        request.session["is_loggedin"] = True

        return redirect("user_homepage")

    return render(request, "user_login.html", {"data_form": data_form})


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

    if request.user.is_authenticated and not request.user.is_superuser:
        return redirect("user_homepage")

    errors = {}

    if request.method == "POST":

        email = (request.POST.get("email") or "").strip()
        if not email:
            errors["email"] = "Email is required."
        elif "@" not in email or "." not in email:
            errors["email"] = "Enter a valid email address."
        else:
            try:
                user = CustomUser.objects.filter(email=email).first()
            except Exception as e:
                print("DB ERROR:", e)
                errors["server"] = "Unable to process request. Try again later."
                return render(request, "forgot_password.html", {"errors": errors})

            if not user:
                errors["email"] = "Email is not registered."

            elif user.is_superuser:
                errors["email"] = "This email is not allowed for password reset."

        if errors:
            return render(request, "forgot_password.html", {"errors": errors})
        try:
            otp = str(random.randint(100000, 999999))

            request.session["forgot_email"] = email
            request.session["forgot_otp"] = otp
            request.session["forgot_otp_time"] = timezone.now().isoformat()
            send_mail(
                subject="Sipzy - Password Reset OTP",
                message=(
                    f"Hello,\n\nYour OTP for resetting your Sipzy password is {otp}. "
                    f"It will expire in 5 minutes.\n\nThank you!"
                ),
                from_email="sipzy505@gmail.com",
                recipient_list=[email],
                fail_silently=False,
            )

            return redirect("forgot_password_otp")

        except Exception as e:
            print("FORGOT PASSWORD ERROR:", e)
            errors["server"] = "Failed to send OTP. Please try again."
            return render(request, "forgot_password.html", {"errors": errors})

    return render(request, "forgot_password.html")


@never_cache
def forgot_password_otp(request):

    if request.user.is_authenticated and not request.user.is_superuser:
        return redirect("user_homepage")
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

    if request.user.is_authenticated and not request.user.is_superuser:
        return redirect("user_homepage")

    email = request.session.get("forgot_email")
    verified = request.session.get("forgot_verified")

    if not email or not verified:
        return redirect("forgot_password")

    errors = {}

    if request.method == "POST":
        password = request.POST.get("password")
        confirm_password = request.POST.get("confirm_password")

        if not password:
            errors["password"] = "Password is required."
        elif not PASSWORD_REGEX.match(password):
            errors["password"] = (
                "Password must be at least 8 characters long "
                "and include letters and numbers."
            )

        if password and confirm_password and password != confirm_password:
            errors["confirm_password"] = "Passwords do not match."

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

    if request.user.is_authenticated and not request.user.is_superuser:
        return redirect("user_homepage")

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






