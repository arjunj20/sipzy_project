from django.shortcuts import render, redirect, get_object_or_404
from django.db.models import Q, Min, Count, Avg
from django.core.paginator import Paginator
from .models import Products, Category, Brand, ProductVariants
from cart.views  import cart_page
from cart.utils import get_user_cart,recalculate_cart_totals
from cart.models import CartItems
from decimal import Decimal, ROUND_HALF_UP
from django.db import transaction
from django.views.decorators.cache import never_cache


@never_cache
def userproduct_list(request):
   
    if not request.user.is_authenticated or request.user.is_superuser:
        return redirect("user_login")

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

    search = request.GET.get("search", "")
    if search:
        products = products.filter(
            Q(name__icontains=search) |
            Q(description__icontains=search) |
            Q(brand__name__icontains=search) |
            Q(category__name__icontains=search)
        )

    selected_categories = request.GET.getlist("category")
    if selected_categories:
        products = products.filter(category__id__in=selected_categories)

    selected_brands = request.GET.getlist("brand")
    if selected_brands:
        products = products.filter(brand__id__in=selected_brands)

    price_filter = request.GET.get("price")
    if price_filter:
        if price_filter == "0-500":
            products = products.filter(variants__price__lte=500)
        elif price_filter == "500-1000":
            products = products.filter(variants__price__gte=500, variants__price__lte=1000)
        elif price_filter == "1000-2000":
            products = products.filter(variants__price__gte=1000, variants__price__lte=2000)
        elif price_filter == "2000-5000":
            products = products.filter(variants__price__gte=2000, variants__price__lte=5000)
        elif price_filter == "5000+":
            products = products.filter(variants__price__gte=5000)

    products = products.distinct()

    sort_option = request.GET.get("sort", "default")
    if sort_option == "price_low_high":
        products = products.annotate(min_price=Min("variants__price")).order_by("min_price")
    elif sort_option == "price_high_low":
        products = products.annotate(min_price=Min("variants__price")).order_by("-min_price")
    elif sort_option == "name_asc":
        products = products.order_by("name")
    elif sort_option == "name_desc":
        products = products.order_by("-name")
    else:
        products = products.order_by("-created_at")

    products = products.prefetch_related("variants")

    paginator = Paginator(products, 8)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    for product in page_obj:
        variant = product.variants.order_by("price").first()
        product.default_variant = variant

    qs = request.GET.copy()
    if "page" in qs:
        qs.pop("page")
    querystring = qs.urlencode()

    price_ranges = {
        "0-500": "Under ₹500",
        "500-1000": "₹500 - ₹1,000",
        "1000-2000": "₹1,000 - ₹2,000",
        "2000-5000": "₹2,000 - ₹5,000",
        "5000+": "Above ₹5,000",
    }

    return render(request, "userproduct_list.html", {
        "products": page_obj,
        "categories": Category.objects.filter(is_active=True),
        "brands": Brand.objects.filter(is_active=True),
        "search": search,
        "selected_categories": selected_categories,
        "selected_brands": selected_brands,
        "price_filter": price_filter,
        "sort_option": sort_option,
        "querystring": querystring,
        "price_ranges": price_ranges,
    })


@never_cache
def product_details(request, uuid):
    if not request.user.is_authenticated or request.user.is_superuser:
        return redirect("landing_page")

    product = get_object_or_404(Products, uuid=uuid)

    if not product.is_active:
        return render(request, "product_unavailable.html", 
                     {"message": "this product is currently unavailable"})
    
    primary_variant = product.variants.order_by("price").first()
    
    variant_id = request.GET.get('variant')
    selected_variant = primary_variant
    
    if variant_id:
        try:
            selected_variant = product.variants.get(id=variant_id, is_active=True)
        except ProductVariants.DoesNotExist:
            selected_variant = primary_variant
    
    quantity = request.GET.get('quantity', 1)
    try:
        quantity = int(quantity)
        if quantity < 1:
            quantity = 1
        elif quantity > selected_variant.stock:
            quantity = selected_variant.stock
    except (ValueError, TypeError):
        quantity = 1
    
    average_rating = 4.5  
    review_count = 128    
    
    related_products = Products.objects.filter(
        category=product.category,
        is_active=True
    ).exclude(id=product.id)[:4]
    
    discount_percentage = 0
    if selected_variant.price < primary_variant.price:
        discount_percentage = int(
            ((primary_variant.price - selected_variant.price) / primary_variant.price) * 100
        )
    
    total_price = selected_variant.price * quantity
    
    all_images = []
    for variant in product.variants.all():
        all_images.append({
            'url': variant.primary_image.url,
            'alt': variant.variant,
            'variant_id': variant.id,
            'is_variant': True
        })
    
    for image in product.images.all():
        all_images.append({
            'url': image.image.url,
            'alt': product.name,
            'variant_id': None,
            'is_variant': False
        })
    
    current_image = request.GET.get('image')
    if current_image:
        main_image = current_image
    else:
        main_image = selected_variant.primary_image.url
    
    message = request.session.pop("message", None)
    error = request.session.pop("error", None)

    context = {
        'product': product,
        'primary_variant': primary_variant,
        'selected_variant': selected_variant,
        'quantity': quantity,
        'total_price': total_price,
        'average_rating': average_rating,
        'review_count': review_count,
        'related_products': related_products,
        'discount_percentage': discount_percentage,
        'reviews': [],  
        'all_images': all_images,
        'main_image': main_image,
        'message': message,
        "error" : error,
    }
    
    return render(request, 'userproduct_details.html', context)

from decimal import Decimal, ROUND_HALF_UP
from django.db import transaction
from django.shortcuts import redirect, get_object_or_404
from django.views.decorators.cache import never_cache
@never_cache
def add_to_cart(request):
    if not request.user.is_authenticated or request.user.is_superuser:
        return redirect("user_login")

    if request.method != "POST":
        return redirect("userproduct_list")

    variant_id = request.POST.get("variant_id")
    
    try:
        qty = int(request.POST.get("quantity", 1))
    except (ValueError, TypeError):
        qty = 1

    if qty < 1:
        qty = 1
    
    variant = get_object_or_404(ProductVariants, id=variant_id, is_active=True)
    ITEM_LIMIT = 5

    if variant.stock == 0:
        request.session["error"] = "This variant is out of stock."
        return redirect("product_details", product_id=variant.product.id)

    if qty > variant.stock:
        qty = variant.stock
        request.session["error"] = f"Only {variant.stock} units available in stock."
        return redirect("product_details", product_id=variant.product.id)

    if qty > ITEM_LIMIT:
        request.session["error"] = f"Users can only select a maximum of {ITEM_LIMIT} units per item."
        return redirect("product_details", product_id=variant.product.id)

    def compute_money(unit_price, gst_rate, quantity):
        u = Decimal(str(unit_price))
        g = Decimal(str(gst_rate or 0))

        unit_tax = (u * g / Decimal("100")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        tax_amount = (unit_tax * quantity).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        price_without_tax = (u * quantity).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        total_with_tax = (price_without_tax + tax_amount).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

        return unit_tax, tax_amount, total_with_tax

    gst_rate = getattr(variant, "gst_rate", 18.0)
    unit_tax, tax_for_qty, total_with_tax = compute_money(variant.price, gst_rate, qty)

    with transaction.atomic():
        cart = get_user_cart(request.user)
        cart_item = CartItems.objects.select_for_update().filter(cart=cart, variant=variant).first()

        if cart_item:
            new_qty = cart_item.quantity + qty
            max_allowed = min(variant.stock, ITEM_LIMIT)

            if new_qty > max_allowed:
                request.session["error"] = f"Maximum limit reached! You can only add {max_allowed - cart_item.quantity} more units."
                return redirect("product_details", product_id=variant.product.id)

            _, new_tax, new_total = compute_money(variant.price, gst_rate, new_qty)

            cart_item.quantity = new_qty
            cart_item.tax_amount = new_tax
            cart_item.total_price = new_total
            cart_item.save()
            request.session["message"] = "Item quantity updated in cart"
        else:
            CartItems.objects.create(
                cart=cart,
                variant=variant,
                quantity=qty,
                tax_amount=tax_for_qty,
                total_price=total_with_tax,
            )
            request.session["message"] = "Item added to cart successfully"

        recalculate_cart_totals(cart)

    return redirect("product_details", product_id=variant.product.id)

                  
