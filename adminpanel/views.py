from django.shortcuts import render,redirect

from django.contrib.auth import authenticate, login, logout


def admin_dashboard(request):
    return render(request, "admin_dashboard.html")


def admin_login(request):

    errors = {}

    if request.method == 'POST':
        email = request.POST.get("email")
        password = request.POST.get("password")

        if not email:
            errors["email"] = "username should be filled.."
        if not password:
            errors["password"] = "password should be filled.."
        if errors:
            return render(request, "admin_login.html", {"errors": errors})

        user = authenticate(request, email=email, password=password)

        if user is not None and user.is_superuser:
            login(request, user)
            return redirect("admin_dashboard")
        else:
            errors["invalid"] = "Invalid credentials.."
            return render(request, "admin_login.html", {"errors": errors})     
        
    return render(request, "admin_login.html")