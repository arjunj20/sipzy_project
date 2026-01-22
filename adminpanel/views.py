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
from wallet.models import Wallet, WalletTransaction



from django.shortcuts import render
from django.utils import timezone
from datetime import timedelta, date
from django.db.models import Sum, Count
from orders.models import Order

from decimal import Decimal

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
def product_edit(request, uuid):

    if not request.user.is_authenticated or not request.user.is_superuser:
        return redirect('admin_login')
    
    product = get_object_or_404(Products, uuid=uuid)
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
            return redirect("product_edit", uuid=product.uuid)

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
                url = _upload_to_cloudinary(img, folder=f"products/{product.uuid}")
                ProductImage.objects.create(product=product, image=url)

            return redirect("product_edit", uuid=product.uuid)

   
    return render(request, "product_edit.html", {
        "product": product,
        "brands": brands,
        "categories": categories,
        "variants": variants
    })




@never_cache
@transaction.atomic
def product_image_delete(request, image_id):

    if not request.user.is_authenticated or not request.user.is_superuser:
        return redirect('admin_login')
    
    errors = {}
    image = get_object_or_404(ProductImage, pk=image_id)
    uuid = image.product.uuid

    if request.method == "POST":
        if not image:
            errors["image"] = "Image not found."
            return render(request, "product_edit.html", {
                "errors": errors
            })

        image.delete()
        return redirect("product_edit", uuid=uuid)

    return redirect("product_edit", uuid=uuid)

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

from django.core.paginator import Paginator
from django.db.models import Q
from django.views.decorators.cache import never_cache
@never_cache
def admin_order_item_list(request):

    if not request.user.is_authenticated or not request.user.is_superuser:
        return redirect('admin_login')

    search = request.GET.get("search", "").strip()
    status_filter = request.GET.get("status", "").strip()
    sort = request.GET.get("sort", "-created_at")

    allowed_sorts = {"created_at", "-created_at", "status", "-status"}
    if sort not in allowed_sorts:
        sort = "-created_at"

    items_qs = (
        OrderItem.objects
        .select_related(
            "order",
            "product",
            "variant",
            "order__user",
            "return_request"
        )
    )

    if search:
        items_qs = items_qs.filter(
            Q(sub_order_id__icontains=search) |
            Q(order__order_number__icontains=search) |
            Q(product__name__icontains=search) |
            Q(order__user__fullname__icontains=search) |
            Q(order__user__email__icontains=search)
        )

    if status_filter:
        items_qs = items_qs.filter(status=status_filter)

    items_qs = items_qs.order_by(sort)

    paginator = Paginator(items_qs, 8)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    return render(request, "suborder_list.html", {
        "items": page_obj,
        "search": search,
        "status_filter": status_filter,
        "sort_by": sort,
        "status_choices": OrderItem.ITEM_STATUS_CHOICES, 
    })


@never_cache
def admin_order_item_detail(request, uuid):
    if not request.user.is_authenticated or not request.user.is_superuser:
        return redirect('admin_login')
    
    item = get_object_or_404(OrderItem.objects.select_related("order", "product", "variant", "order__user", "return_request"), uuid=uuid)
    return render(request, "suborder_detail.html", {"item": item})


from decimal import Decimal
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.views.decorators.http import require_POST
from django.views.decorators.cache import never_cache

from orders.models import OrderItem
from wallet.models import Wallet, WalletTransaction


@never_cache
@require_POST
def update_suborder_status(request, item_id):
    if not request.user.is_authenticated or not request.user.is_superuser:
        return redirect("admin_login")

    item = get_object_or_404(OrderItem, id=item_id)
    action = request.POST.get("status")

    if action in ["approved", "rejected"]:
        if not hasattr(item, "return_request"):
            return JsonResponse({
                "success": False,
                "message": "No return request found"
            })

        rr = item.return_request
        rr.status = action
        rr.save(update_fields=["status"])

        if action == "rejected":
            item.status = "delivered"
            item.save(update_fields=["status"])

        return JsonResponse({
            "success": True,
            "message": f"Return {action} successfully"
        })

    if action == "returned":
        if not hasattr(item, "return_request") or item.return_request.status != "approved":
            return JsonResponse({
                "success": False,
                "message": "Return must be approved first"
            })

        if item.return_request.status == "refunded":
            return JsonResponse({
                "success": False,
                "message": "Refund already processed"
            })

        item.status = "returned"
        item.save(update_fields=["status"])

        if item.variant:
            item.variant.stock += item.quantity
            item.variant.save(update_fields=["stock"])


        refund_amount = item.net_paid_amount

        order = item.order

        if order.payment_method.lower() in ["razorpay", "wallet"] and order.payment_status == "paid":

            wallet, _ = Wallet.objects.get_or_create(
                user=order.user,
                defaults={"balance": Decimal("0.00")}
            )

            wallet.balance += refund_amount
            wallet.save(update_fields=["balance"])

            WalletTransaction.objects.create(
                wallet=wallet,
                transaction_type=WalletTransaction.CREDIT,
                amount=refund_amount,
                order=order,
                status="completed",
                description=f"Refund for returned item {item.sub_order_id}"
            )

            item.return_request.status = "refunded"
            item.return_request.save(update_fields=["status"])

        order.recalculate_totals()

        return JsonResponse({
            "success": True,
            "message": "Item marked as returned and order totals updated"
        })


    VALID_STATUS_TRANSITIONS = {
        "pending": ["processing", "cancelled"],
        "processing": ["shipped", "cancelled"],
        "shipped": ["delivered"],
    }

    current = item.status

    if current not in VALID_STATUS_TRANSITIONS:
        return JsonResponse({
            "success": False,
            "message": "Status cannot be changed at this stage"
        })

    if action not in VALID_STATUS_TRANSITIONS[current]:
        return JsonResponse({
            "success": False,
            "message": f"Cannot change status from {current} to {action}"
        })

    item.status = action
    item.save(update_fields=["status"])

    return JsonResponse({
        "success": True,
        "message": "Status updated successfully"
    })


def admin_variant_list(request, product_uuid):

    product = get_object_or_404(Products, uuid=product_uuid)
    variants = product.variants.all()
    errors={}
    success = None

    if request.method == 'POST':
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

        if primary_image and not errors:
            upload = cloudinary_upload(primary_image)
            img_url = upload.get("secure_url")

        if errors:
            return render(request, "admin/variant_list.html", {
                "product": product,
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

        success = "Variant added successfully"
        return redirect("variant_list", product_uuid=product.uuid)


    return render(request, "variant_list.html", {
        "product": product,
        "variants": variants,
        "errors": errors,
        "success": success
            })


def admin_edit_variant(request, uuid):
    variant = get_object_or_404(ProductVariants, uuid=uuid)
    errors = {}
    success = None

    if request.method == "POST":
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
                errors["price"] = "Invalid price."

        if not stock:
            errors["stock"] = "Stock is required."
        else:
            try:
                stock_val = int(stock)
                if stock_val < 0:
                    errors["stock"] = "Stock cannot be negative."
            except:
                errors["stock"] = "Invalid stock value."

        if not errors:
            variant.variant = variant_name
            variant.price = price_val
            variant.stock = stock_val

            if primary_image:
                upload = cloudinary_upload(primary_image)
                variant.primary_image = upload.get("secure_url")

            variant.save()
            success = "Variant updated successfully"
            return redirect("variant_list", product_uuid=variant.product.uuid)

    return render(request, "edit_variant.html", {
        "variant": variant,
        "errors": errors,
        "success": success
    })

from datetime import timedelta, datetime, time

@never_cache
@transaction.atomic
def variant_delete(request, uuid):

    if not request.user.is_authenticated or not request.user.is_superuser:
        return redirect('admin_login')

    variant = get_object_or_404(ProductVariants, uuid=uuid)
    product_uuid = variant.product.uuid  

    if request.method == "POST":
        variant.delete()

    return redirect("variant_list", product_uuid=product_uuid)

def admin_sales_report(request):
    filter_type = request.GET.get("filter", "today")
    start_date = request.GET.get("start_date")
    end_date = request.GET.get("end_date")

    now = timezone.now()
    today = now.date()

    orders = Order.objects.filter(payment_status="paid")

    if filter_type == "today":
        start_dt = timezone.make_aware(datetime.combine(today, time.min))
        end_dt = timezone.make_aware(datetime.combine(today, time.max))
        orders = orders.filter(created_at__range=(start_dt, end_dt))

    elif filter_type == "week":
        orders = orders.filter(created_at__gte=now - timedelta(days=7))

    elif filter_type == "month":
        start_dt = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        orders = orders.filter(created_at__gte=start_dt)

    elif filter_type == "year":
        start_dt = now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
        orders = orders.filter(created_at__gte=start_dt)

    elif filter_type == "custom" and start_date and end_date:
        start_dt = timezone.make_aware(
            datetime.combine(datetime.strptime(start_date, "%Y-%m-%d"), time.min)
        )
        end_dt = timezone.make_aware(
            datetime.combine(datetime.strptime(end_date, "%Y-%m-%d"), time.max)
        )
        orders = orders.filter(created_at__range=(start_dt, end_dt))

    summary = orders.aggregate(
        total_orders=Count("id"),
        total_sales=Sum("total"),
        total_discount=Sum("coupon_discount"),
    )

  
    order_items_qs = (
        OrderItem.objects
        .select_related("order", "product")
        .filter(order__in=orders)
        .order_by("-created_at")
    )

    paginator = Paginator(order_items_qs, 10)  
    page_number = request.GET.get("page")
    order_items = paginator.get_page(page_number)

    context = {
        "orders": orders.order_by("-created_at"),
        "order_items": order_items,   
        "summary": summary,
        "filter_type": filter_type,
        "start_date": start_date,
        "end_date": end_date,
    }

    return render(request, "sales_report.html", context)

import openpyxl
from django.http import HttpResponse
from django.utils import timezone
from datetime import timedelta
from orders.models import Order

def sales_report_excel(request):
    filter_type = request.GET.get("filter", "today")
    start_date = request.GET.get("start_date")
    end_date = request.GET.get("end_date")

    orders = Order.objects.filter(payment_status="paid", total__gt=0)
    today = timezone.now().date()

    if filter_type == "today":
        orders = orders.filter(created_at__date=today)

    elif filter_type == "week":
        orders = orders.filter(created_at__date__gte=today - timedelta(days=7))

    elif filter_type == "month":
        orders = orders.filter(
            created_at__year=today.year,
            created_at__month=today.month
        )

    elif filter_type == "year":
        orders = orders.filter(created_at__year=today.year)

    elif filter_type == "custom" and start_date and end_date:
        orders = orders.filter(created_at__date__range=[start_date, end_date])

    total_orders = orders.count()
    total_sales = orders.aggregate(Sum("total"))["total__sum"] or 0
    total_discount = orders.aggregate(Sum("coupon_discount"))["coupon_discount__sum"] or 0

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Sales Report"

    ws.append(["Overall Sales Count", total_orders])
    ws.append(["Overall Order Amount", float(total_sales)])
    ws.append(["Overall Discount", float(total_discount)])
    ws.append([]) 


    ws.append(["Order No", "Date", "Total", "Discount"])


    for order in orders:
        ws.append([
            order.order_number,
            order.created_at.date(),
            float(order.total),
            float(order.coupon_discount),
        ])

    response = HttpResponse(
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    response["Content-Disposition"] = "attachment; filename=sales_report.xlsx"
    wb.save(response)
    return response
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

def sales_report_pdf(request):
    filter_type = request.GET.get("filter", "today")
    start_date = request.GET.get("start_date")
    end_date = request.GET.get("end_date")

    orders = Order.objects.filter(payment_status="paid", total__gt=0).order_by('-created_at')
    today = timezone.now().date()

    if filter_type == "today":
        orders = orders.filter(created_at__date=today)
    elif filter_type == "week":
        orders = orders.filter(created_at__date__gte=today - timedelta(days=7))
    elif filter_type == "month":
        orders = orders.filter(created_at__year=today.year, created_at__month=today.month)
    elif filter_type == "year":
        orders = orders.filter(created_at__year=today.year)
    elif filter_type == "custom" and start_date and end_date:
        orders = orders.filter(created_at__date__range=[start_date, end_date])

    total_orders = orders.count()
    total_sales = orders.aggregate(Sum("total"))["total__sum"] or 0
    total_discount = orders.aggregate(Sum("coupon_discount"))["coupon_discount__sum"] or 0

    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = f"attachment; filename=Sales_Report_{today}.pdf"

    doc = SimpleDocTemplate(response, pagesize=A4, rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=30)
    elements = []
    styles = getSampleStyleSheet()

    title_style = ParagraphStyle('TitleStyle', parent=styles['Heading1'], textColor=colors.HexColor("#0f172a"), fontSize=18, spaceAfter=10)
    subtitle_style = ParagraphStyle('SubtitleStyle', fontSize=10, textColor=colors.grey, spaceAfter=20)

    elements.append(Paragraph("AdminHub - Sales Report", title_style))
    elements.append(Paragraph(f"Generated on: {timezone.now().strftime('%Y-%m-%d %H:%M')}", subtitle_style))
    elements.append(Spacer(1, 12))

    summary_data = [
        ["Total Orders", "Total Revenue", "Total Discounts"],
        [str(total_orders), f"Rs. {total_sales}", f"Rs. {total_discount}"]
    ]
    summary_table = Table(summary_data, colWidths=[170, 170, 170])
    summary_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#6366f1")),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor("#f8fafc")),
        ('TEXTCOLOR', (0, 1), (-1, -1), colors.HexColor("#1e293b")),
        ('FONTSIZE', (0, 1), (-1, -1), 14),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica-Bold'),
        ('GRID', (0, 0), (-1, -1), 1, colors.HexColor("#e2e8f0")),
        ('ROUNDEDCORNERS', [10, 10, 10, 10]),
    ]))
    elements.append(summary_table)
    elements.append(Spacer(1, 30))

    table_data = [["Order Number", "Date", "Discount", "Total Amount"]]
    for order in orders:
        table_data.append([
            f"#{order.order_number}",
            order.created_at.strftime('%Y-%m-%d'),
            f"Rs. {order.coupon_discount}",
            f"Rs. {order.total}"
        ])

    main_table = Table(table_data, colWidths=[140, 120, 120, 130])
    main_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#0f172a")), 
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
        ('GRID', (0, 1), (-1, -1), 0.5, colors.grey),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor("#f1f5f9")])
    ]))
    
    elements.append(main_table)
    doc.build(elements)
    return response


def admin_inventory(request):
    products = Products.objects.prefetch_related('variants').all().order_by('-created_at')
    
    context = {
        'products': products,
    }
    return render(request, 'admin_inventory.html', context)