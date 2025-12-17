from django.shortcuts import render,redirect
from products.models import Products
from .models import ProductOffer
from django.core.exceptions import ValidationError


def offer_list(request):
    offers = ProductOffer.objects.filter(is_active=True)
    return render(request, "offer_list.html",{"offers": offers})


def add_product_offer(request):

    errors = {}
    if not request.user.is_authenticated or not request.user.is_superuser:
        return redirect("user_login")
    products= Products.objects.filter(is_active=True)

    if request.method == 'POST':
        product_id = request.POST.get("product")
        discount_percent_raw = request.POST.get("discount_percent")
        offer_name = request.POST.get("offer_name")
        start_date = request.POST.get("start_date")
        end_date = request.POST.get("end_date")
        is_active = True if request.POST.get("is_active") else False
        
        if not all([product_id, offer_name, discount_percent_raw, start_date, end_date]):
            errors["empty"] = "All fields are required"
            return render(request, "add_product_offer.html", {
                "errors": errors, "products": products
            })
        
        try:        
            product = Products.objects.get(id=product_id)
            discount_percent = int(discount_percent_raw)
            offr = ProductOffer(
                    product=product,
                    discount_percent=discount_percent,
                    offer_name=offer_name,
                    start_date=start_date,
                    end_date=end_date,
                    is_active=is_active
                )           
            offr.full_clean()
            offr.save()
            return redirect("offer_list")
        except ValueError:
            errors["discount"] = "Discount should be a valid number"
        except Products.DoesNotExist:
            errors["product"] = "Invalid product selected"

        except ValidationError as e:
            errors["validation"] = e.messages

        except Exception:
            errors["error"] = "Something went wrong. Please try again."
    return render(request, "add_product_offer.html", {"products": products, "errors": errors})