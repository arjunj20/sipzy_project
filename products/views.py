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

from offers.utils import get_best_offer_for_product, apply_offer


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
        variant = min(product.variants.all(), key=lambda v: v.price, default=None)
        product.default_variant = variant

        product.final_price = None
        product.applied_offer = None
        if variant:
            offer = get_best_offer_for_product(product)
            if offer:
                product.final_price = apply_offer(variant.price, offer)
                product.applied_offer = offer
            else:
                product.final_price = variant.price
                product.applied_offer = None


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
    
    variant_uuid = request.GET.get('variant')
    selected_variant = primary_variant
    
    if variant_uuid:
        try:
            selected_variant = product.variants.get(uuid=variant_uuid, is_active=True)
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
    ).exclude(id=product.id).prefetch_related("variants")[:4]

    for rp in related_products:
        variant = rp.variants.order_by("price").first()
        rp.default_variant = variant

        rp.offer = None
        rp.final_price = None

        if variant:
            offer = get_best_offer_for_product(rp)
            if offer:
                rp.offer = offer
                rp.final_price = apply_offer(variant.price, offer)
            else:
                rp.final_price = variant.price

    
    offer = None

    final_unit_price = selected_variant.price

    offer = get_best_offer_for_product(product)

    if offer:
        final_unit_price = apply_offer(selected_variant.price, offer)
    
    total_price = final_unit_price * quantity
    
    all_images = []
    for variant in product.variants.all():
        all_images.append({
            'url': variant.primary_image.url,
            'alt': variant.variant,
            'variant_uuid': variant.uuid,
            'is_variant': True
        })
    
    for image in product.images.all():
        all_images.append({
            'url': image.image.url,
            'alt': product.name,
            'variant_uuid': None,
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
        "offer": offer,
        "final_unit_price": final_unit_price,
        'primary_variant': primary_variant,
        'selected_variant': selected_variant,
        'quantity': quantity,
        'total_price': total_price,
        'average_rating': average_rating,
        'review_count': review_count,
        'related_products': related_products,
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
    qty = max(1, int(request.POST.get("quantity", 1)))

    variant = get_object_or_404(ProductVariants, id=variant_id, is_active=True)

    # 🔐 Stock & limit checks
    ITEM_LIMIT = 5
    qty = min(qty, variant.stock, ITEM_LIMIT)

    # ✅ APPLY OFFER HERE
    offer = get_best_offer_for_product(variant.product)
    unit_price = apply_offer(variant.price, offer) if offer else variant.price

    # ✅ TAX ON DISCOUNTED PRICE
    gst_rate = getattr(variant, "gst_rate", 18)
    unit_tax = (unit_price * Decimal(gst_rate) / 100).quantize(Decimal("0.01"))
    tax_amount = unit_tax * qty
    total_price = (unit_price * qty) + tax_amount

    with transaction.atomic():
        cart = get_user_cart(request.user)

        item = CartItems.objects.select_for_update().filter(
            cart=cart,
            variant=variant
        ).first()

        if item:
            item.quantity += qty
            item.unit_price = unit_price
            item.tax_amount = unit_tax * item.quantity
            item.total_price = (unit_price * item.quantity) + item.tax_amount
            item.save()
        else:
            CartItems.objects.create(
                cart=cart,
                variant=variant,
                quantity=qty,
                unit_price=unit_price,
                tax_amount=tax_amount,
                total_price=total_price,
            )

        recalculate_cart_totals(cart)

    request.session["message"] = "Item added to cart"
    return redirect("product_details", uuid=variant.product.uuid)
