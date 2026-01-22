from django.utils import timezone
from .models import ProductOffer,CategoryOffer
from decimal import Decimal

def deactivate_expired_offers():
    today = timezone.now().date()
    ProductOffer.objects.filter(
        is_active=True,
        end_date__lt=today
    ).update(is_active=False)

def deactivate_expired_category_offers():
    today = timezone.now().date()

    CategoryOffer.objects.filter(
        is_active=True,
        end_date__lt = today
    ).update(is_active=False)

def get_best_offer_for_product(product):

    offers = []

    today = timezone.now().date()

    product_offer = ProductOffer.objects.filter(
        product=product,
        is_active=True,
        start_date__lte=today,
        end_date__gte=today
    ).first()

    if product_offer:
        offers.append(product_offer)
    
    category_offer = CategoryOffer.objects.filter(
        category=product.category,
        is_active=True,
        start_date__lte=today,
        end_date__gte=today
    ).first()

    if category_offer:
        offers.append(category_offer)
    
    if not offers:
        return None
    
    return max(offers, key=lambda o: o.discount_percent)

def apply_offer(price, offer):

    if not offer:
        return price
    
    discount_percent = Decimal(offer.discount_percent)
    discount_amount = (price * discount_percent)/Decimal(100)
    final_price = price - discount_amount

    return final_price.quantize(Decimal("0.01"))
    
