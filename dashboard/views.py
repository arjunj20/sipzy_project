from django.shortcuts import render, redirect
from django.http import JsonResponse
from orders.models import Order, OrderItem 
from django.db.models.functions import TruncDate, TruncMonth, TruncYear, TruncWeek
from django.db.models import Sum
from django.views.decorators.cache import never_cache
from django.utils import timezone
from datetime import datetime, timedelta
from authenticate.models import CustomUser
from django.db.models import Count
from orders.models import Order


@never_cache
def admin_dashboard(request):
    if not request.user.is_authenticated or not request.user.is_superuser:
        return redirect('admin_login')
    users_count = CustomUser.objects.aggregate(count=Count("fullname"))

    total_orders = Order.objects.aggregate(order_count=Count("uuid"))
    top_selling_products = OrderItem.objects.exclude(status__in=['cancelled', 'returned']).values('product__name').annotate(total_sold=Sum('quantity')).order_by('-total_sold')[:10]
    top_selling_categories = OrderItem.objects.exclude(status__in=["cancelled", "returned"]).values("product__category__name").annotate(total_sold=Sum("quantity")).order_by("-total_sold")[:11]
    top_selling_brands = OrderItem.objects.exclude(status__in=["cancelled", "returned"]).values("product__brand__name").annotate(total_sold=Sum("quantity")).order_by("-total_sold")[:10]
    
        
    context = {
        "total_users": users_count['count'],
        "total_orders": total_orders["order_count"],
        "top_selling_products": top_selling_products,
        "top_selling_categories": top_selling_categories,
        "top_selling_brands": top_selling_brands,

    }
    
    return render(request, "dashboard/admin_dashboard.html", context)


def visualization_data(request):
    if not request.user.is_authenticated or not request.user.is_superuser:
        return redirect("admin_login")

    grouping_method = request.GET.get("grouping_method", "Daily")

    query_set = OrderItem.objects.filter(
        order__payment_status="paid"
    ).exclude(
        status__in=["cancelled", "returned"]
    )

    if grouping_method == "Daily":
        grouping_data = (
            query_set
            .annotate(period=TruncDate("order__created_at", tzinfo=timezone.get_current_timezone()))
            .values("period")
            .annotate(total=Sum("net_paid_amount"))
            .order_by("period")
        )
        date_format = "%Y-%m-%d"

    elif grouping_method == "Weekly":
        grouping_data = (
            query_set
            .annotate(period=TruncWeek("order__created_at", tzinfo=timezone.get_current_timezone()))
            .values("period")
            .annotate(total=Sum("net_paid_amount"))
            .order_by("period")
        )
        date_format = "%Y-%m-%d"

    elif grouping_method == "Monthly":
        grouping_data = (
            query_set
            .annotate(period=TruncMonth("order__created_at", tzinfo=timezone.get_current_timezone()))
            .values("period")
            .annotate(total=Sum("net_paid_amount"))
            .order_by("period")
        )
        date_format = "%Y-%m"

    elif grouping_method == "Yearly":
        grouping_data = (
            query_set
            .annotate(period=TruncYear("order__created_at", tzinfo=timezone.get_current_timezone()))
            .values("period")
            .annotate(total=Sum("net_paid_amount"))
            .order_by("period")
        )
        date_format = "%Y"

    else:
        return JsonResponse({"error": "Invalid grouping method"}, status=400)
    
    data = []
    for item in grouping_data:
        if item["period"] is not None:
            data.append({
                "label": item["period"].strftime(date_format),
                "value": float(item["total"] or 0)
            })

    return JsonResponse({
        "grouping": grouping_method,
        "data": data
    }) 
