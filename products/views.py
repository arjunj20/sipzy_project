from django.shortcuts import render, redirect, get_object_or_404
from django.db.models import Q, Min, Count, Avg
from django.core.paginator import Paginator
from .models import Products, Category, Brand

from django.views.decorators.cache import never_cache


@never_cache
def userproduct_list(request):

    if not request.user.is_authenticated or request.user.is_superuser:
        return redirect("landing_page")

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
        variant = product.variants.order_by("-price").first()
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
def product_details(request, product_id):

    if not request.user.is_authenticated or request.user.is_superuser:
        return redirect("landing_page")

    product = get_object_or_404(Products, id=product_id)

    if not product.is_active:
        return render(request, "product_unavailable.html", {"message": "this product is currently unavailable"})
    
    if not product.is_active:
        return redirect('product_list')
    
    primary_variant = product.variants.first()
    
    variant_id = request.GET.get('variant')
    selected_variant = primary_variant
    
    if variant_id:
        try:
            selected_variant = product.variants.get(id=variant_id)
        except ProductVariants.DoesNotExist:
            selected_variant = primary_variant
    
    average_rating = 4.5  
    review_count = 128    
    
    related_products = Products.objects.filter(
        category=product.category,
        is_active=True
    ).exclude(id=product.id)[:4]
    
    discount_percentage = 0
    if selected_variant.price < primary_variant.price:
        discount_percentage = int(((primary_variant.price - selected_variant.price) / primary_variant.price) * 100)
    
    context = {
        'product': product,
        'primary_variant': primary_variant,
        'selected_variant': selected_variant,
        'average_rating': average_rating,
        'review_count': review_count,
        'related_products': related_products,
        'discount_percentage': discount_percentage,
        'reviews': [],  
    }
    
    return render(request, 'userproduct_details.html', context)
