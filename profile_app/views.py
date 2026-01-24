from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.cache import never_cache
from django.contrib.auth.decorators import login_required
from cloudinary.uploader import upload as cloudinary_upload
from authenticate.models import CustomUser
import re
import base64
from django.core.files.base import ContentFile

from django.contrib.auth.decorators import login_required
from django.views.decorators.cache import never_cache
from django.core.mail import send_mail
from django.utils import timezone
from django.contrib import messages
import random
from django.contrib.auth import  logout
from django.db.models import Count
from orders.models import Order
from authenticate.models import Address
from django.conf import settings
from wallet.models import Wallet
from referal.models import Referral


PASSWORD_REGEX = re.compile(r"^(?=.*[A-Za-z])(?=.*\d)[A-Za-z\d@#$!%*?&]{8,}$")


@login_required
@never_cache
def user_profile(request):
    if not request.user.is_authenticated or request.user.is_superuser:
        return redirect("user_login")
    
    user = request.user
    addresses = user.addresses.all()
    counts = Order.objects.filter(user=user).count()
    wallet, _ = Wallet.objects.get_or_create(user=user)


    referral, _ = Referral.objects.get_or_create(
        referrer=user,
        is_used=False
    )

    referral_link = request.build_absolute_uri(
        f"/user-signup/?ref={referral.token}"
    )

    return render(request, "user_profile.html", {
        "user": user,
        "addresses": addresses,
        "counts": counts,
        "wallet": wallet,
        "referral_link": referral_link,
    })

@login_required
def edit_profile(request):

    if request.user.is_superuser:
        return redirect("user_login")

    user = request.user
    errors = {}

    FULLNAME_REGEX = re.compile(r'^[A-Za-z .]+$')

    if request.method == "POST":
        fullname = request.POST.get("fullname", "").strip()
        cropped_image_data = request.POST.get("cropped_image")

        if not fullname:
            errors["fullname"] = "Name is required."
        elif len(fullname) < 3:
            errors["fullname"] = "Name must be at least 3 characters."
        elif not FULLNAME_REGEX.match(fullname):
            errors["fullname"] = "Name can contain only letters, spaces, and dot (.)."

        if errors:
            return render(
                request,
                "edit_profile.html",
                {"user": user, "errors": errors}
            )

        user.fullname = fullname

        if cropped_image_data and cropped_image_data.startswith("data:image"):
            try:
                upload_result = cloudinary_upload(
                    cropped_image_data,
                    folder="profile_images",
                    transformation=[
                        {"width": 500, "height": 500, "crop": "fill"}
                    ]
                )
                user.profile_image = upload_result.get("secure_url")
            except Exception:
                errors["profile_image"] = "Failed to upload image."
                return render(
                    request,
                    "edit_profile.html",
                    {"user": user, "errors": errors}
                )

        user.save()
        return redirect("user_profile")

    return render(
        request,
        "edit_profile.html",
        {"user": user, "errors": errors}
    )


@login_required
@never_cache
def change_email(request):

    if not request.user.is_authenticated or request.user.is_superuser:
        return redirect("user_login")
    
    errors = {}

    if request.method == "POST":
        new_email = request.POST.get("email", "").strip().lower()
        user = request.user

        if not new_email:
            errors["email"] = "Email is required"

        elif len(new_email) > 254:
            errors["email"] = "Email is too long"

        elif new_email == user.email:
            errors["email"] = "This is already your current email"

        elif not re.match(
            r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$',
            new_email
        ):
            errors["email"] = "Enter a valid email address"

        elif CustomUser.objects.filter(email=new_email).exists():
            errors["email"] = "This email is already in use"

        if errors:
            return render(request, "change_email.html", {
                "errors": errors,
                "email": new_email
            })

        otp = random.randint(100000, 999999)

        request.session["change_email"] = {
            "email": new_email,
            "otp": otp,
            "otp_time": timezone.now().isoformat()
        }

        send_mail(
            subject="Email Change Verification OTP",
            message = f"""
                        Hi there,

                        We received a request to change the email address associated with your account.

                        Your One-Time Password (OTP) is: {otp}

                        ⏳ This OTP is valid for 2 minutes only.

                        For your security, please do not share this OTP with anyone.  
                        If you did not request this change, no action is required.

                        Regards,  
                        Sipzy Support Team
                        """,
            from_email="sipzy505@gmail.com",
            recipient_list=[new_email],
            fail_silently=False,
        )

        return redirect("email_otp")

    return render(request, "change_email.html")



from django.contrib.auth.decorators import login_required
from django.views.decorators.cache import never_cache
from django.shortcuts import render, redirect
from django.contrib import messages
from django.utils import timezone
from django.utils.dateparse import parse_datetime

@login_required
@never_cache
def email_otp(request):

    if not request.user.is_authenticated or request.user.is_superuser:
        return redirect("user_login")
    
    errors = {}
    data = request.session.get("change_email")

    if not data:
        messages.error(request, "Session expired. Please try again.")
        return redirect("change_email")

    correct_otp = str(data["otp"])

    try:
        otp_time = parse_datetime(data["otp_time"])
        otp_time = otp_time.astimezone(timezone.get_current_timezone())
    except Exception:
        messages.error(request, "OTP error. Please try again.")
        return redirect("change_email")

    now = timezone.now()
    elapsed = (now - otp_time).total_seconds()
    allowed_time = 120  
    remaining_time = max(0, int(allowed_time - elapsed))

    if request.method == "POST":
     
        otp_digits = [
            request.POST.get(f"otp{i}", "") for i in range(1, 7)
        ]

        if any(d.strip() == "" for d in otp_digits):
            errors["otp"] = "Please enter all 6 digits of the OTP."

        if not all(d.isdigit() for d in otp_digits):
            errors["otp"] = "OTP must contain only numbers."

        entered_otp = "".join(otp_digits)

        if remaining_time <= 0:
            errors["otp"] = "OTP expired. Please resend OTP."

        if entered_otp != correct_otp:
            errors["otp"] = "Invalid OTP."

        if errors:
            return render(request, "email_otp.html", {
                "errors": errors,
                "remaining_time": remaining_time
            })


        request.user.email = data["email"]
        request.user.save()

        del request.session["change_email"]
        messages.success(request, "Email updated successfully.")
        return redirect("user_profile")

    return render(request, "email_otp.html", {
        "remaining_time": remaining_time
    })



@login_required
@never_cache
def resend_email_otp(request):
    if not request.user.is_authenticated or request.user.is_superuser:
        return redirect("user_login")

    data = request.session.get("change_email")
    if not data:
        messages.error(request, "Session expired. Please try again.")
        return redirect("change_email")

    new_otp = random.randint(100000, 999999)

    data["otp"] = new_otp
    data["otp_time"] = timezone.now().isoformat()
    request.session["change_email"] = data
    send_mail(
        subject="Your OTP for Email Change",
        message=f"Your OTP is {new_otp}. It is valid for 5 minutes.",
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[data["email"]],
        fail_silently=False,
    )

    messages.success(request, "A new OTP has been sent to your email.")
    return redirect("email_otp")



@login_required
@never_cache
def change_password(request):

    if not request.user.is_authenticated or request.user.is_superuser:
        return redirect("user_login")

    errors = {}

    if request.method == "POST":
        old_password = request.POST.get("old_password")
        new_password = request.POST.get("new_password")
        confirm_password = request.POST.get("confirm_password")

        if not old_password:
            errors["old_password"] = "Old password is required."
        elif not request.user.check_password(old_password):
            errors["old_password"] = "Old password is incorrect."

        if not new_password:
            errors["new_password"] = "New password is required."
        elif not PASSWORD_REGEX.match(new_password):
            errors["new_password"] = (
                "Password must be at least 8 characters long "
                "and include letters and numbers."
            )

        if new_password and confirm_password and new_password != confirm_password:
            errors["confirm_password"] = "Passwords do not match."

        if errors:
            return render(request, "change_password.html", {"errors": errors})

        request.user.set_password(new_password)
        request.user.save()

        logout(request)
        messages.success(
            request,
            "Password changed successfully. Please login again."
        )
        return redirect("user_login")

    return render(request, "change_password.html")




@login_required
@never_cache
def add_addresses(request):

    if not request.user.is_authenticated or request.user.is_superuser:
        return redirect("user_login")

    errors = {}

    FULLNAME_REGEX = re.compile(r'^[A-Za-z .]+$')
    PHONE_REGEX = re.compile(r'^[6-9]\d{9}$')
    CITY_STATE_REGEX = re.compile(r'^[A-Za-z ]+$')
    PINCODE_REGEX = re.compile(r'^\d{6}$')

    if request.method == "POST":
        full_name = request.POST.get("full_name", "").strip()
        phone = request.POST.get("phone_number", "").strip()
        line1 = request.POST.get("address_line1", "").strip()
        line2 = request.POST.get("address_line2", "").strip()
        city = request.POST.get("city", "").strip()
        state = request.POST.get("state", "").strip()
        pincode = request.POST.get("pincode", "").strip()

        # 1️⃣ Full Name
        if not full_name:
            errors["full_name"] = "Full name is required."
        elif len(full_name) < 3:
            errors["full_name"] = "Full name must be at least 3 characters."
        elif not FULLNAME_REGEX.match(full_name):
            errors["full_name"] = "Name can contain only letters, spaces, and dot (.)."

        # 2️⃣ Phone Number
        if not phone:
            errors["phone_number"] = "Phone number is required."
        elif not PHONE_REGEX.match(phone):
            errors["phone_number"] = "Enter a valid 10-digit phone number."

        # 3️⃣ Address Line 1
        if not line1:
            errors["address_line1"] = "Address line is required."
        elif len(line1) < 5:
            errors["address_line1"] = "Address must be at least 5 characters."

        # 4️⃣ City
        if not city:
            errors["city"] = "City is required."
        elif not CITY_STATE_REGEX.match(city):
            errors["city"] = "City can contain only letters and spaces."

        # 5️⃣ State
        if not state:
            errors["state"] = "State is required."
        elif not CITY_STATE_REGEX.match(state):
            errors["state"] = "State can contain only letters and spaces."

        # 6️⃣ Pincode
        if not pincode:
            errors["pincode"] = "Pincode is required."
        elif not PINCODE_REGEX.match(pincode):
            errors["pincode"] = "Enter a valid 6-digit pincode."

        if errors:
            return render(request, "add_addresses.html", {"errors": errors})

        Address.objects.create(
            user=request.user,
            full_name=full_name,
            phone_number=phone,
            address_line1=line1,
            address_line2=line2,
            city=city,
            state=state,
            pincode=pincode,
        )

        return redirect("user_profile")

    return render(request, "add_addresses.html")



@login_required
@never_cache
def edit_addresses(request, uuid):

    if not request.user.is_authenticated or request.user.is_superuser:
        return redirect("user_login")

    address = get_object_or_404(
        Address,
        uuid=uuid,
        user=request.user
    )

    errors = {}

    # Same regex rules everywhere
    FULLNAME_REGEX = re.compile(r'^[A-Za-z .]+$')
    PHONE_REGEX = re.compile(r'^[6-9]\d{9}$')
    CITY_STATE_REGEX = re.compile(r'^[A-Za-z ]+$')
    PINCODE_REGEX = re.compile(r'^\d{6}$')

    if request.method == "POST":
        full_name = request.POST.get("full_name", "").strip()
        phone = request.POST.get("phone_number", "").strip()
        line1 = request.POST.get("address_line1", "").strip()
        line2 = request.POST.get("address_line2", "").strip()
        city = request.POST.get("city", "").strip()
        state = request.POST.get("state", "").strip()
        pincode = request.POST.get("pincode", "").strip()

        # 1️⃣ Full Name
        if not full_name:
            errors["full_name"] = "Full name is required."
        elif len(full_name) < 3:
            errors["full_name"] = "Full name must be at least 3 characters."
        elif not FULLNAME_REGEX.match(full_name):
            errors["full_name"] = "Name can contain only letters, spaces, and dot (.)."

        # 2️⃣ Phone
        if not phone:
            errors["phone_number"] = "Phone number is required."
        elif not PHONE_REGEX.match(phone):
            errors["phone_number"] = "Enter a valid 10-digit phone number."

        # 3️⃣ Address Line 1
        if not line1:
            errors["address_line1"] = "Address line is required."
        elif len(line1) < 5:
            errors["address_line1"] = "Address must be at least 5 characters."

        # 4️⃣ City
        if not city:
            errors["city"] = "City is required."
        elif not CITY_STATE_REGEX.match(city):
            errors["city"] = "City can contain only letters and spaces."

        # 5️⃣ State
        if not state:
            errors["state"] = "State is required."
        elif not CITY_STATE_REGEX.match(state):
            errors["state"] = "State can contain only letters and spaces."

        # 6️⃣ Pincode
        if not pincode:
            errors["pincode"] = "Pincode is required."
        elif not PINCODE_REGEX.match(pincode):
            errors["pincode"] = "Enter a valid 6-digit pincode."

        if errors:
            return render(
                request,
                "edit_addresses.html",
                {
                    "address": address,
                    "errors": errors
                }
            )

        # Update fields only after validation
        address.full_name = full_name
        address.phone_number = phone
        address.address_line1 = line1
        address.address_line2 = line2
        address.city = city
        address.state = state
        address.pincode = pincode

        address.save()
        return redirect("user_profile")

    return render(
        request,
        "edit_addresses.html",
        {"address": address}
    )

@never_cache
def delete_address(request, uuid):

    if not request.user.is_authenticated or request.user.is_superuser:
        return redirect("user_login")

    address = get_object_or_404(
        Address,
        uuid=uuid,
        user=request.user   
    )

    address.delete()
    return redirect("user_profile")