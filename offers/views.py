from django.shortcuts import render,redirect, get_object_or_404
from products.models import Products, Category
from .models import ProductOffer, CategoryOffer
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.core.paginator import Paginator
from .utils import deactivate_expired_offers,deactivate_expired_category_offers


def offer_list(request):
    deactivate_expired_offers()
    offers_qs = ProductOffer.objects.all().order_by("-created_at")
    paginator = Paginator(offers_qs, 8)
    page_number = request.GET.get("page")
    offers = paginator.get_page(page_number)
    return render(request, "offer_list.html",{"offers": offers})

def add_product_offer(request):

    if not request.user.is_authenticated or not request.user.is_superuser:
        return redirect("user_login")

    errors = {}
    products = Products.objects.filter(is_active=True)

    if request.method == "POST":
        product_id = request.POST.get("product")
        offer_name = request.POST.get("offer_name")
        discount_percent_raw = request.POST.get("discount_percent")
        min_product_price_raw = request.POST.get("min_product_price")
        max_product_price_raw = request.POST.get("max_product_price")
        start_date = request.POST.get("start_date")
        end_date = request.POST.get("end_date")
        is_active = True if request.POST.get("is_active") else False

        required_fields = {
            "product": product_id,
            "offer_name": offer_name,
            "discount_percent": discount_percent_raw,
            "min_product_price": min_product_price_raw,
            "max_product_price": max_product_price_raw,
            "start_date": start_date,
            "end_date": end_date,
        }

        for field, value in required_fields.items():
            if not value:
                errors[field] = "This field is required"

        if errors:
            return render(request, "add_product_offer.html", {
                "products": products,
                "errors": errors
            })

        try:
            product = Products.objects.get(id=product_id)

            offer = ProductOffer(
                product=product,
                offer_name=offer_name,
                discount_percent=int(discount_percent_raw),
                min_product_price=int(min_product_price_raw),
                max_product_price=int(max_product_price_raw),
                start_date=start_date,
                end_date=end_date,
                is_active=is_active
            )

            offer.full_clean()
            offer.save()
            return redirect("offer_list")

        except Products.DoesNotExist:
            errors["product"] = "Invalid product selected"
        except ValueError:
            errors["number"] = "Discount and prices must be valid numbers"
        except ValidationError as e:
            errors["validation"] = e.messages
        except Exception:
            errors["error"] = "Something went wrong. Please try again."

    return render(request, "add_product_offer.html", {
        "products": products,
        "errors": errors
    })


def edit_product_offer(request, uuid):

    prod = get_object_or_404(ProductOffer, uuid=uuid)
    errors = {}

    if request.method == "POST":
        offer_name = request.POST.get("offer_name")
        discount_percent_raw = request.POST.get("discount_percent")
        min_product_price_raw = request.POST.get("min_product_price")
        max_product_price_raw = request.POST.get("max_product_price")
        start_date = request.POST.get("start_date")
        end_date = request.POST.get("end_date")
        is_active = True if request.POST.get("is_active") else False

        required_fields = {
            "offer_name": offer_name,
            "discount_percent": discount_percent_raw,
            "min_product_price": min_product_price_raw,
            "max_product_price": max_product_price_raw,
            "start_date": start_date,
            "end_date": end_date,
        }

        for field, value in required_fields.items():
            if not value:
                errors[field] = "This field is required"

        if errors:
            return render(request, "edit_product_offer.html", {
                "offer": prod,
                "errors": errors
            })

        try:
            prod.offer_name = offer_name
            prod.discount_percent = int(discount_percent_raw)
            prod.min_product_price = int(min_product_price_raw)
            prod.max_product_price = int(max_product_price_raw)
            prod.start_date = start_date
            prod.end_date = end_date
            prod.is_active = is_active

            prod.full_clean()
            prod.save()
            return redirect("offer_list")

        except ValueError:
            errors["number"] = "Discount and prices must be valid numbers"
        except ValidationError as e:
            errors["validation"] = e.messages
        except Exception:
            errors["error"] = "Something went wrong. Please try again."

    return render(request, "edit_product_offer.html", {
        "offer": prod,
        "errors": errors
    })


def deactivate_product_offer(request, uuid):
    if not request.user.is_authenticated or not request.user.is_superuser:
        return redirect("admin_login")
    offr = get_object_or_404(ProductOffer, uuid=uuid)
    offr.is_active = False
    offr.save()

    return redirect("offer_list")

def activate_product_offer(request, uuid):
    if not request.user.is_authenticated or not request.user.is_superuser:
        return redirect("admin_login")

    offr = get_object_or_404(ProductOffer, uuid=uuid)

    if offr.is_expired:
        return redirect("offer_list")

    ProductOffer.objects.filter(
        product=offr.product,
        is_active=True
    ).exclude(uuid=offr.uuid).update(is_active=False)

    offr.is_active = True
    offr.save()

    return redirect("offer_list")

def category_offer_list(request):  
    deactivate_expired_category_offers()

    offers = CategoryOffer.objects.all()


    return render(request, "category_offer_list.html",{"offers": offers})

def category_add_offer(request):

    if not request.user.is_authenticated or not request.user.is_superuser:
        return redirect("admin_login")

    errors = {}
    categories = Category.objects.filter(is_active=True)

    if request.method == 'POST':
        category_id = request.POST.get("category")
        offer_name = request.POST.get("offer_name")
        discount_percent_raw = request.POST.get("discount_percent")
        start_date = request.POST.get("start_date")
        end_date = request.POST.get("end_date")
        is_active = True if request.POST.get("is_active") else False

        required_fields = {
            "category": category_id,
            "offer_name": offer_name,
            "discount_percent": discount_percent_raw,
            "start_date": start_date,
            "end_date": end_date,
        }

        for field, value in required_fields.items():
            if not value:
                errors[field] = "This field is required"

        if errors:
            return render(request, "add_category_offer.html", {
                "errors": errors,
                "categories": categories
            })

        try:
            category = get_object_or_404(Category, id=category_id)
            discount_percent = int(discount_percent_raw)

            offer = CategoryOffer(
                category=category,
                offer_name=offer_name,
                discount_percent=discount_percent,
                start_date=start_date,
                end_date=end_date,
                is_active=is_active
            )

            offer.full_clean()
            offer.save()

            return redirect("category_offer_list")

        except ValueError:
            errors["discount_percent"] = "Discount must be a valid number"

        except IntegrityError:
            errors["category"] = "An active offer already exists for this category"

        except ValidationError as e:
            errors["validation"] = e.messages

        except Exception:
            errors["error"] = "Something went wrong. Please try again."

    return render(request, "add_category_offer.html", {
        "categories": categories,
        "errors": errors
    })


def edit_category_offer(request, uuid):

    if not request.user.is_authenticated or not request.user.is_superuser:
        return redirect("admin_login")

    offer = get_object_or_404(CategoryOffer, uuid=uuid)
    errors = {}

    if offer.is_expired:
        errors["expired"] = "Expired offers cannot be edited."

    if request.method == "POST" and not offer.is_expired:
        offer_name = request.POST.get("offer_name")
        discount_percent_raw = request.POST.get("discount_percent")
        start_date = request.POST.get("start_date")
        end_date = request.POST.get("end_date")
        is_active = True if request.POST.get("is_active") else False

        required_fields = {
            "offer_name": offer_name,
            "discount_percent": discount_percent_raw,
            "start_date": start_date,
            "end_date": end_date,
        }

        for field, value in required_fields.items():
            if not value:
                errors[field] = "This field is required"

        if errors:
            return render(request, "edit_category_offer.html", {
                "offer": offer,
                "errors": errors
            })

        try:
            offer.offer_name = offer_name
            offer.discount_percent = int(discount_percent_raw)
            offer.start_date = start_date
            offer.end_date = end_date
            offer.is_active = is_active

            offer.full_clean()
            offer.save()

            return redirect("category_offer_list")

        except ValueError:
            errors["discount_percent"] = "Discount must be a valid number"

        except IntegrityError:
            errors["category"] = "An active offer already exists for this category"

        except ValidationError as e:
            errors["validation"] = e.messages

        except Exception:
            errors["error"] = "Something went wrong. Please try again."

    return render(request, "edit_category_offer.html", {
        "offer": offer,
        "errors": errors
    })

def deactivate_category_offer(request, uuid):
    if not request.user.is_authenticated or not request.user.is_superuser:
        return redirect("admin_login")

    offer = get_object_or_404(CategoryOffer, uuid=uuid)

    offer.is_active = False
    offer.save(update_fields=["is_active"])

    return redirect("category_offer_list")


def deactivate_category_offer(request, uuid):
    if not request.user.is_authenticated or not request.user.is_superuser:
        return redirect("admin_login")

    offer = get_object_or_404(CategoryOffer, uuid=uuid)

    offer.is_active = False
    offer.save(update_fields=["is_active"])

    return redirect("category_offer_list")


def activate_category_offer(request, uuid):
    if not request.user.is_authenticated or not request.user.is_superuser:
        return redirect("admin_login")

    offer = get_object_or_404(CategoryOffer, uuid=uuid)
    if offer.is_expired:
        return redirect("category_offer_list")

    CategoryOffer.objects.filter(
        category=offer.category,
        is_active=True
    ).exclude(uuid=offer.uuid).update(is_active=False)

    offer.is_active = True
    offer.save(update_fields=["is_active"])

    return redirect("category_offer_list")