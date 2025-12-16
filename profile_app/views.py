from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.cache import never_cache
from django.contrib.auth.decorators import login_required
from cloudinary.uploader import upload as cloudinary_upload
from authenticate.models import CustomUser

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



@login_required
@never_cache
def user_profile(request):
    if not request.user.is_authenticated or request.user.is_superuser:
        return redirect("user_login")
    
    user = request.user
    addresses = user.addresses.all()
    counts = Order.objects.filter(user=user).count()

    return render(request, "user_profile.html", {
        "user": user,
        "addresses": addresses,
        "counts": counts,
    })

@login_required
def edit_profile(request):
    if not request.user.is_authenticated or request.user.is_superuser:
        return redirect("user_login")
    user = request.user
    errors = {}

    if request.method == "POST":
        fullname = request.POST.get("fullname")
        image = request.FILES.get("profile_image")

        if not fullname:
            errors["fullname"] = "Name is required"

        if image and not errors:
            upload = cloudinary_upload(
                image,
                folder="profile_images"
            )
            img_url = upload.get("secure_url")
            public_id = upload.get("public_id")

        if errors:
            return render(request, "user/edit_profile.html", {
                "user": user,
                "errors": errors
            })

        user.fullname = fullname

        if image:
            user.profile_image = img_url

        user.save()
        return redirect("user_profile")

    return render(request, "edit_profile.html", {
        "user": user,
        "errors": errors
    })

@login_required
@never_cache
def change_email(request):

    if not request.user.is_authenticated or request.user.is_superuser:
        return redirect("user_login")
    
    if request.method == "POST":
        new_email = request.POST.get("email")
        errors = {}
        if not new_email:
            errors["email"] = "Email is required"
        elif CustomUser.objects.filter(email=new_email).exists():
            errors["email"] = "This email is already in use"

        if errors:
            return render(request, "change_email.html", {
                "errors": errors
            })
        otp = random.randint(100000, 999999)

        request.session["change_email"] = {
            "email": new_email,
            "otp": otp,
            "otp_time": timezone.now().isoformat()
        }
        send_mail(
            subject="Email Change Verification OTP",
            message=f"Your OTP to change email is {otp}",
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
    allowed_time = 100  
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

        if not new_password:
            errors["new_password"] = "New password is required."

        if not confirm_password:
            errors["confirm_password"] = "Confirm password is required."

        if not request.user.check_password(old_password):
            errors["old_password"] = "Old password is incorrect."

        if new_password and confirm_password and new_password != confirm_password:
            errors["confirm_password"] = "Passwords do not match."

        if errors:
            return render(request, "change_password.html", {
                "errors": errors
            })


        request.user.set_password(new_password)
        request.user.save()

        logout(request)
        messages.success(request, "Password changed successfully. Please login again.")
        return redirect("user_login")

    return render(request, "change_password.html")



@login_required
@never_cache
def add_addresses(request):

    if not request.user.is_authenticated or request.user.is_superuser:
        return redirect("user_login")
    errors = {}

    if request.method == "POST":
        full_name = request.POST.get("full_name")
        phone = request.POST.get("phone_number")
        line1 = request.POST.get("address_line1")
        line2 = request.POST.get("address_line2")
        city = request.POST.get("city")
        state = request.POST.get("state")
        pincode = request.POST.get("pincode")

        if not full_name:
            errors["full_name"] = "Full name is required"
        if not phone:
            errors["phone_number"] = "Phone number is required"
        if not line1:
            errors["address_line1"] = "Address line is required"
        if not city:
            errors["city"] = "City is required"
        if not state:
            errors["state"] = "State is required"
        if not pincode:
            errors["pincode"] = "Pincode is required"

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

    if request.method == "POST":
        address.full_name = request.POST.get("full_name")
        address.phone_number = request.POST.get("phone_number")
        address.address_line1 = request.POST.get("address_line1")
        address.address_line2 = request.POST.get("address_line2")
        address.city = request.POST.get("city")
        address.state = request.POST.get("state")
        address.pincode = request.POST.get("pincode")

        if not address.full_name:
            errors["full_name"] = "Full name is required"

        if errors:
            return render(request, "edit_address.html", {
                "address": address,
                "errors": errors
            })

        address.save()
        return redirect("user_profile")

    return render(request, "edit_addresses.html", {
        "address": address
    })

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