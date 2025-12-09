from django.shortcuts import render, redirect, get_object_or_404
from products.models import Category, Products, ProductVariants, ProductImage,Brand
from authenticate.models import CustomUser
from cloudinary.uploader import upload as cloudinary_upload

from django.views.decorators.cache import never_cache
from django.contrib.auth import authenticate, login, logout
from django.db.models import Q,Count
from django.core.paginator import Paginator
import cloudinary.uploader
from django.db import transaction
from decimal import Decimal, InvalidOperation
from orders.models import OrderItem
from django.http import JsonResponse
from django.views.decorators.http import require_POST



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
    
    errors = {}
    if request.method == "POST":
        name = request.POST.get("name")
        description = request.POST.get("description")
        active = request.POST.get("active") == "on"

        if name and Category.objects.filter(name__iexact=name).exists():
            errors["name"] = "This category is exists.."
        elif not name:
            errors["name"] = "Name must be filled..."

        if not description:
            errors["description"] = "description must be filled.."
        else:
            word_count = len(description.split())
            if word_count < 3:
                errors["description"] = "description must have atleast 3 words"

       

        if errors:
            categories = Category.objects.all().order_by("-id")
            return render(request, "category_list.html", {
                "errors": errors,
                "name": name,
                "description": description,
                "active": active,
                "open_create_modal": True,
                "categories": categories,
            })
        Category.objects.create( name=name, description=description, is_active=active
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

    errors = {}

    if request.method == "POST":
        name = request.POST.get("name", "").strip()
        description = request.POST.get("description", "").strip()
        active = request.POST.get("active") == "on"

        if not name:
            errors["name"] = "Name is required"
        elif Category.objects.filter(name__iexact=name).exclude(id=id).exists():
            errors["name"] = "Name already taken"

        if not description:
            errors["description"] = "Description is required"
        elif len(description.split()) < 3:
            errors["description"] = "Description must contain at least 3 words"

        if errors:
            categories = Category.objects.all().order_by("-id")

            return render(request, "category_list.html", {
                "errors_edit": errors,      
                "open_edit_modal": True,   
                "edit_data": {
                    "id": id,
                    "name": name,
                    "description": description,
                    "active": active,
                },
                "categories": categories,
            })
        category.name = name
        category.description = description
        category.is_active = active
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


@never_cache
def user_list(request):
    if not request.user.is_authenticated or not request.user.is_superuser:
        return redirect("admin_login")

    users = CustomUser.objects.filter(is_superuser=False).order_by("-joined_date")

    search_query = request.GET.get("search", "")   

    inactive_count = 0
    active_count = 0
    all_count = 0
    for i in users:
        if i.is_active == False:
            inactive_count += 1
        else:
            active_count += 1
        all_count += 1

    if search_query:
        users = users.filter(Q(fullname__icontains=search_query)|Q(email__icontains=search_query))

    paginator = Paginator(users, 5)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    context = {
        "users": page_obj,
        "page_obj": page_obj,
        "search_query": search_query,
        "blocked_users": inactive_count,
        "active_users": active_count,
        "total_users": all_count,
    }
    return render(request, "user_list.html", context)

@never_cache
def block_user(request, id):
    
    if not request.user.is_authenticated or not request.user.is_superuser:
        return redirect("admin_login")
    user = get_object_or_404(CustomUser, id=id)

    user.is_active = False
    user.save()
    return redirect("user_list")


@never_cache
def unblock_user(request, id):

    if not request.user.is_authenticated or not request.user.is_superuser:
        return redirect("admin_login")

    user = get_object_or_404(CustomUser, id=id)

    user.is_active = True
    user.save()
    return redirect("user_list")

@never_cache
def brand_list(request):
    if not request.user.is_authenticated or not request.user.is_superuser:
        return redirect("admin_login")

    brands = Brand.objects.all().order_by("name")

    search_query = request.GET.get("search", "")

    total_brands = brands.count()

    if search_query:
        brands = brands.filter(
            Q(name__icontains=search_query) |
            Q(description__icontains=search_query)
        )

    paginator = Paginator(brands, 5) 
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    context = {
        "brands": page_obj,
        "page_obj": page_obj,
        "search_query": search_query,
        "total_brands": total_brands,
    }
    return render(request, "brand_list.html", context)
@never_cache
def brand_add(request):

    if not request.user.is_authenticated or not request.user.is_superuser:
        return redirect('admin_login')
    
    errors = {}

    if request.method == "POST":
        name = request.POST.get("name", "").strip()
        description = request.POST.get("description", "").strip()
        is_active = request.POST.get("is_active") == "on"

        if not name:
            errors["name"] = "Brand name is required"
        elif Brand.objects.filter(name__iexact=name).exists():
            errors["name"] = "This brand already exists"

        if not description:
            errors["description"] = "Description is required"
        elif len(description.split()) < 3:
            errors["description"] = "Description must contain at least 3 words"

        if errors:
            brands = Brand.objects.all().order_by("-id")
            return render(request, "brand_list.html", {
                "errors": errors,
                "name": name,
                "description": description,
                "is_active": is_active,
                "open_create_modal": True,
                "brands": brands,
            })

        Brand.objects.create(name=name, description=description, is_active=is_active)
        return redirect("brand_list")

    return redirect("brand_list")

@never_cache
def brand_edit(request, id):

    if not request.user.is_authenticated or not request.user.is_superuser:
        return redirect("admin_login")

    brand = get_object_or_404(Brand, id=id)
    errors = {}

    if request.method == "POST":
        name = request.POST.get("name", "").strip()
        description = request.POST.get("description", "").strip()
        is_active = request.POST.get("is_active") == "on"

        if not name:
            errors["name"] = "Brand name is required"
        elif Brand.objects.filter(name__iexact=name).exclude(id=id).exists():
            errors["name"] = "Brand name already exists"

        if not description:
            errors["description"] = "Description is required"
        elif len(description.split()) < 3:
            errors["description"] = "Description must contain at least 3 words"

        if errors:
            brands = Brand.objects.all().order_by("-id")
            return render(request, "brand_list.html", {
                "errors_edit": errors,
                "open_edit_modal": True,
                "edit_data": {
                    "id": id,
                    "name": name,
                    "description": description,
                    "is_active": is_active,
                },
                "brands": brands,
            })

        brand.name = name
        brand.description = description
        brand.is_active = is_active
        brand.save()
        return redirect("brand_list")

    return redirect("brand_list")



@never_cache
def brand_delete(request, id):
    if not request.user.is_authenticated or not request.user.is_superuser:
        return redirect('admin_login')
    
    brand = get_object_or_404(Brand, id=id)
    brand.is_active = False
    brand.save()
    return redirect("brand_list")

import cloudinary.uploader

def _upload_to_cloudinary(image_file, folder):
    result = cloudinary.uploader.upload(
        image_file,
        folder=folder,
        overwrite=True,
        resource_type="auto"
    )
    return result["secure_url"]


@never_cache
def product_list(request):

    if not request.user.is_authenticated or not request.user.is_superuser:
        return redirect('admin_login')
    
    products_qs = Products.objects.select_related('brand', 'category').all().order_by('-created_at')
    brands = Brand.objects.filter(is_active=True)
    categories = Category.objects.filter(is_active=True)


    paginator = Paginator(products_qs, 5)  
    page_number = request.GET.get("page")
    products = paginator.get_page(page_number)


    return render(request, "product_list.html", {
        "products": products,
        "brands": brands,
        "categories": categories,
    })



@never_cache
@transaction.atomic
def product_create(request):

    if not request.user.is_authenticated or not request.user.is_superuser:
        return redirect('admin_login')
    
    products_qs = Products.objects.select_related('brand', 'category').all().order_by('-created_at')
    brands = Brand.objects.filter(is_active=True)
    categories = Category.objects.filter(is_active=True)
    errors = {}

    if request.method == "POST":
        name = request.POST.get("name", "").strip()
        brand_id = request.POST.get("brand") or None
        category_id = request.POST.get("category") or None
        description = request.POST.get("description", "")
        is_active = request.POST.get("is_active") == "on"

        if not name:
            errors["name"] = "Product name is required."

        if Products.objects.filter(name__iexact=name).exists():
            errors["name"] = "A product with this name already exists."

        if len(description.split()) < 3:
            errors["description"] = "Description must contain at least 3 words."

        images = request.FILES.getlist("images[]")
        if len(images) < 3:
            errors["images"] = "Please upload at least 3 images."
        paginator = Paginator(products_qs, 5)  
        page_number = request.GET.get("page")
        products = paginator.get_page(page_number)

        if errors:
            return render(request, "product_list.html", {
                "products": products,
                "brands": brands,
                "categories": categories,
                "errors": errors,
                "open_modal": True  
            })
        product = Products.objects.create(
            name=name,
            brand_id=brand_id,
            category_id=category_id,
            description=description,
            is_active=is_active
        )

        for img in images:
            url = _upload_to_cloudinary(img, folder=f"products/{product.id}")
            ProductImage.objects.create(product=product, image=url)

        return redirect("product_list")
    return redirect("product_list") 

@never_cache
@transaction.atomic
def product_edit(request, product_id):

    if not request.user.is_authenticated or not request.user.is_superuser:
        return redirect('admin_login')
    
    product = get_object_or_404(Products, pk=product_id)
    brands = Brand.objects.filter(is_active=True)
    categories = Category.objects.filter(is_active=True)
    variants = product.variants.all().order_by('-created_at')

    errors = {}
    success = None

    if request.method == "POST":
        action = request.POST.get("action")

        if action == "edit_product":
            name = request.POST.get("name", "").strip()
            brand_id = request.POST.get("brand")
            category_id = request.POST.get("category")
            description = request.POST.get("description", "").strip()
            is_active = request.POST.get("is_active") == "on"

            if not name:
                errors["name"] = "Product name is required."
            if not brand_id:
                errors["brand"] = "Brand is required."
            if not category_id:
                errors["category"] = "Category is required."
            if len(description.split()) < 3:
                errors["description"] = "Description must contain at least 3 words."

            if errors:
                return render(request, "product_edit.html", {
                    "product": product,
                    "brands": brands,
                    "categories": categories,
                    "variants": variants,
                    "errors": errors
                })

            product.name = name
            product.brand_id = brand_id
            product.category_id = category_id
            product.description = description
            product.is_active = is_active
            product.save()

            success = "Product updated successfully!"
            return redirect("product_edit", product_id=product.id)

        elif action == "add_images":
            new_images = request.FILES.getlist("images[]")

            if not new_images:
                errors["images"] = "Please select at least one image."
                return render(request, "product_edit.html", {
                    "product": product,
                    "brands": brands,
                    "categories": categories,
                    "variants": variants,
                    "errors": errors
                })

            for img in new_images:
                url = _upload_to_cloudinary(img, folder=f"products/{product.id}")
                ProductImage.objects.create(product=product, image=url)

            return redirect("product_edit", product_id=product.id)

    
        elif action == "add_variant":
            variant_name = request.POST.get("variant", "").strip()
            price = request.POST.get("price", "").strip()
            stock = request.POST.get("stock", "").strip()
            primary_image = request.FILES.get("primary_image")

            if not variant_name:
                errors["variant"] = "Variant name is required."

            if not price:
                errors["price"] = "Price is required."
            else:
                try:
                    price_val = Decimal(price)
                    if price_val <= 0:
                        errors["price"] = "Price must be greater than 0."
                except:
                    errors["price"] = "Price must be a valid number."

            if not stock:
                errors["stock"] = "Stock quantity is required."
            else:
                try:
                    stock_val = int(stock)
                    if stock_val < 0:
                        errors["stock"] = "Stock cannot be negative."
                except:
                    errors["stock"] = "Stock must be a number."

            if not primary_image:
                errors["primary_image"] = "Primary image is required."

            if primary_image:
                upload=cloudinary_upload(primary_image)
                img_url = upload.get("secure_url")
            else:
                errors["primary_image"] = "Primary image is required."

            if errors:
                return render(request, "product_edit.html", {
                    "product": product,
                    "brands": brands,
                    "categories": categories,
                    "variants": variants,
                    "errors": errors
                })
            

            ProductVariants.objects.create(
                product=product,
                variant=variant_name,
                price=price_val,
                stock=stock_val,
                primary_image=img_url,
            )

            return redirect("product_edit", product_id=product.id)

    return render(request, "product_edit.html", {
        "product": product,
        "brands": brands,
        "categories": categories,
        "variants": variants
    })

@never_cache
@transaction.atomic
def variant_delete(request, variant_id):

    if not request.user.is_authenticated or not request.user.is_superuser:
        return redirect('admin_login')
    errors = {}
    variant = get_object_or_404(ProductVariants, pk=variant_id)
    product_id = variant.product.id

    if request.method == "POST":
        if not variant:
            errors["variant"] = "Variant not found."
            return render(request, "product_edit.html", {
                "errors": errors
            })

        variant.delete()
        return redirect("product_edit", product_id=product_id)

    return redirect("product_edit", product_id=product_id)


@never_cache
@transaction.atomic
def product_image_delete(request, image_id):

    if not request.user.is_authenticated or not request.user.is_superuser:
        return redirect('admin_login')
    
    errors = {}
    image = get_object_or_404(ProductImage, pk=image_id)
    product_id = image.product.id

    if request.method == "POST":
        if not image:
            errors["image"] = "Image not found."
            return render(request, "product_edit.html", {
                "errors": errors
            })

        image.delete()
        return redirect("product_edit", product_id=product_id)

    return redirect("product_edit", product_id=product_id)

@never_cache
@transaction.atomic
def product_delete(request, product_id):

    if not request.user.is_authenticated or not request.user.is_superuser:
        return redirect('admin_login')
    
    product = get_object_or_404(Products, id=product_id)

    if request.method == "POST":
        product.is_active = False
        product.save()
        return redirect("product_list")

    return redirect("product_list")

@never_cache
def admin_order_item_list(request):

    search = request.GET.get("search", "")
    status_filter = request.GET.get("status", "")
    sort = request.GET.get("sort", "-created_at")

    items = OrderItem.objects.select_related("order", "product", "variant", "order__user")
    if search:
        items = items.filter(
            Q(sub_order_id__icontains=search) |
            Q(order__order_number__icontains=search) |
            Q(product__name__icontains=search) |
            Q(order__user__fullname__icontains=search) |
            Q(order__user__email__icontains=search)
        )
    if status_filter:
        items = items.filter(status=status_filter)
    items = items.order_by(sort)

    paginator = Paginator(items, 12)
    page = request.GET.get("page")
    items = paginator.get_page(page)

    return render(request, "suborder_list.html", {
        "items": items,
        "search": search,
        "status_filter": status_filter,
        "sort_by": sort,
    })


def admin_order_item_detail(request, item_id):
    item = get_object_or_404(OrderItem.objects.select_related("order", "product", "variant", "order__user"), id=item_id)
    return render(request, "suborder_detail.html", {"item": item})



@require_POST
def update_suborder_status(request, item_id):
    item = get_object_or_404(OrderItem, id=item_id)
    new_status = request.POST.get("status")

    if new_status not in dict(OrderItem.ITEM_STATUS_CHOICES):
        return JsonResponse({"success": False, "message": "Invalid status"})

    item.status = new_status
    item.save()
    return JsonResponse({"success": True, "message": "Status updated successfully"})

