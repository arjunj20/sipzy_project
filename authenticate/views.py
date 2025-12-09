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



@never_cache
def user_signup(request):

    if request.user.is_authenticated and not request.user.is_superuser:
        return redirect("user_homepage")
    
    errors = {}

    if request.method == 'POST':
        fullname = request.POST.get("fullname")
        email = request.POST.get("email")
        password = request.POST.get("password")
        confirmpassword = request.POST.get("confirm_password")
        if not fullname:
            errors["fullname"] = "Full name is required."

        if not email:
            errors["email"] = "Email is required."

        if not password:
            errors["password"] = "Password is required."
        elif len(password) < 6:
            errors["password_length"] = "Password must be at least 6 characters."

        if password and confirmpassword and password != confirmpassword:
            errors["password_match"] = "Passwords do not match."

        if email and CustomUser.objects.filter(email=email).exists():
            errors["email_exist"] = "Email is already registered."

        if fullname and CustomUser.objects.filter(fullname=fullname).exists():
            errors["fullname_exist"] = "Fullname already exists."

        if errors:
            return render(request, "user_signup.html", {"errors": errors})

        try:
            otp = random.randint(100000, 999999)

            request.session["signup_data"] = {
                'fullname': fullname,
                'email': email,
                "password": password,
                'otp': otp,
                "otp_time": timezone.now().isoformat()
            }
            send_mail(
                subject="Sipzy - Email Verification OTP",
                message=(
                    f"Hello {fullname},\n\n"
                    f"Your verification OTP is {otp}. "
                    "It will expire in 5 minutes.\n\nThank you!"
                ),
                from_email="sipzy505@gmail.com",
                recipient_list=[email],
                fail_silently=False,
            )

            return redirect("user_signupotp")

        except Exception as e:
            print("SIGNUP ERROR:", e)
            errors["general"] = "Something went wrong. Please try again."
            return render(request, "user_signup.html", {"errors": errors})

    return render(request, "user_signup.html")

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
        otp_digits = [
            request.POST.get(f'otp{i}', '') for i in range(1, 7)
        ]

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
            del request.session["signup_data"]

            messages.success(request, "Account created successfully!")
            return redirect("user_login")

        except Exception as e:
            print("USER CREATION ERROR:", e)
            errors["server_error"] = "Something went wrong. Please try again."
            return render(request, "user_signupotp.html", {
                "error": errors,
                "remaining_time": remaining_time
            })


    return render(request, "user_signupotp.html", {"remaining_time": remaining_time})

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
  
    return render(request, "landing.html")

@never_cache
def user_login(request):
  
    if request.user.is_authenticated and not request.user.is_superuser:
        return redirect("user_homepage")

    errors = {}

    MAX_ATTEMPTS = 5
    LOCKOUT_SECONDS = 300 

    attempts = request.session.get("login_attempts", 0)
    lockout_time = request.session.get("login_lockout_time")  
    if lockout_time:
        try:
            lockout_dt = timezone.datetime.fromisoformat(lockout_time)
            lockout_dt = lockout_dt.replace(tzinfo=timezone.utc).astimezone(timezone.get_current_timezone())
            if timezone.now() < lockout_dt:
                remaining = int((lockout_dt - timezone.now()).total_seconds())
                minutes = remaining // 60
                seconds = remaining % 60
                errors["locked"] = f"Too many failed attempts. Try again in {minutes}m {seconds}s."
                return render(request, "user_login.html", {"errors": errors})
            else:
                request.session.pop("login_attempts", None)
                request.session.pop("login_lockout_time", None)
                attempts = 0
        except Exception:
            request.session.pop("login_attempts", None)
            request.session.pop("login_lockout_time", None)
            attempts = 0

    if request.method == 'POST':
        email = (request.POST.get("email") or "").strip()
        password = request.POST.get("password") or ""

        if not email:
            errors["email"] = "Email is required."
        elif "@" not in email or "." not in email:
            errors["email_format"] = "Enter a valid email address."

        if not password:
            errors["password"] = "Password is required."

        if errors:
            return render(request, "user_login.html", {"errors": errors})
        try:
            user = authenticate(request, email=email, password=password)
        except Exception as e:
            print("AUTH ERROR:", e)
            errors["server"] = "Authentication service unavailable. Try again later."
            return render(request, "user_login.html", {"errors": errors})

        if user is None:
            attempts += 1
            request.session["login_attempts"] = attempts
            if attempts >= MAX_ATTEMPTS:
                lockout_dt = timezone.now() + timedelta(seconds=LOCKOUT_SECONDS)
                request.session["login_lockout_time"] = lockout_dt.isoformat()
                errors["locked"] = f"Too many failed attempts. Try again in {LOCKOUT_SECONDS//60} minutes."
                return render(request, "user_login.html", {"errors": errors})

            errors["invalid"] = "Invalid email or password."
            remaining = MAX_ATTEMPTS - attempts
            errors["attempts_left"] = f"{remaining} attempt(s) left before lockout."
            return render(request, "user_login.html", {"errors": errors})
        try:
            if not user.is_active:
                errors["inactive"] = "User account is inactive. Contact support."
                return render(request, "user_login.html", {"errors": errors})

            login(request, user)
            request.session["is_loggedin"] = True

            try:
                user.is_loggedin = True
                user.save(update_fields=["is_loggedin"])
            except Exception as e:
                print("USER FLAG SAVE ERROR:", e)
            request.session.pop("login_attempts", None)
            request.session.pop("login_lockout_time", None)

            return redirect("user_homepage")

        except Exception as e:
            print("LOGIN PROCESS ERROR:", e)
            errors["server"] = "Unable to complete login. Try again later."
            return render(request, "user_login.html", {"errors": errors})
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

from django.shortcuts import render
from django.contrib.auth.decorators import login_required

@login_required
def user_profile(request):
    if not request.user.is_authenticated or request.user.is_superuser:
        return redirect("user_login")
    user = request.user
    addresses = user.addresses.all()
    
    context = {
        'user': user,
        'addresses': addresses,
    }
    
    return render(request, 'profile.html', context)




