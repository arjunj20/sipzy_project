from django.utils import timezone
from .models import ProductOffer,CategoryOffer

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