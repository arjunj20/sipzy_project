from django.shortcuts import render, redirect, get_object_or_404
from products.models import Category

from django.views.decorators.cache import never_cache
from django.contrib.auth import authenticate, login, logout
from django.db.models import Q,Count
from django.core.paginator import Paginator


@never_cache
def admin_dashboard(request):

    if not request.user.is_authenticated or not request.user.is_superuser:
        return redirect('admin_login')
    
    return render(request, "admin_dashboard.html")


@never_cache
def admin_login(request):

    if request.user.is_authenticated and request.user.is_superuser:
        return redirect("admin_dashboard")

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


@never_cache
def category_list(request):

    if not request.user.is_authenticated or not request.user.is_superuser:
        return redirect('admin_login')
    search_query = request.GET.get("search", "")

    categories = Category.objects.all().order_by("-created_at")
    total_categories = Category.objects.aggregate(total=Count('id'))
    active_categories = Category.objects.filter(is_active=True)
    count = 0
    for i in active_categories:
        if i.is_active == True:
            count += 1

    if search_query:
        categories = categories.filter(
            Q(name__icontains=search_query)|
            Q(description__icontains=search_query)
        )   

    inactive_categories = Category.objects.filter(is_active=False)
    inactive_count = inactive_categories.count()

    paginator = Paginator(categories, 5)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    context = {
        "categories": page_obj,
        "search_query": search_query,
        "page_obj": page_obj,
        "total_categories": total_categories,
        "count": count,
        'inactive_count': inactive_count
        }

    return render(request, "category_list.html", context)


@never_cache
def category_add(request):

    if not request.user.is_authenticated or not request.user.is_superuser:
        return redirect('admin_login')
    
    if request.method == "POST":
        name = request.POST.get("name")
        description = request.POST.get("description")
        active = request.POST.get("active") == "on"

        Category.objects.create( name=name, description=description, is_active=active, 
        )
        return redirect("category_list")

    return redirect("category_list")


@never_cache
def category_delete(request, id):

    if not request.user.is_authenticated or not request.user.is_superuser:
        return redirect('admin_login')
    
    category = get_object_or_404(Category, id=id)
    category.is_active = False
    category.save()
    return redirect("category_list")


@never_cache
def category_edit(request, id):

    if not request.user.is_authenticated or not request.user.is_superuser:
        return redirect('admin_login')
    category = get_object_or_404(Category, id=id)

    if request.method == "POST":
        category.name = request.POST.get("name")
        category.description = request.POST.get("description")
        category.is_active = request.POST.get("active") == "on"
        category.save()

        return redirect("category_list")

    return redirect("category_list")


@never_cache
def admin_logout(request):
    user = request.user
    if request.user.is_authenticated and request.user.is_superuser:
        user.is_loggedin = False
        user.save()
        logout(request)
    return redirect("admin_login")



