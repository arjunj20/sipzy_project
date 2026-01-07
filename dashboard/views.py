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


from django.shortcuts import render, redirect
from django.http import JsonResponse
from orders.models import Order, OrderItem 
from django.db.models.functions import TruncDate, TruncMonth, TruncYear, TruncWeek
from django.db.models import Sum
from django.utils import timezone
from datetime import timedelta

def visualization_data(request):
    if not request.user.is_authenticated or not request.user.is_superuser:
        return redirect("admin_login")

    grouping_method = request.GET.get("grouping_method", "Daily")

    # Base Query: Paid orders, excluding cancelled/returned
    query_set = OrderItem.objects.filter(
        order__payment_status="paid"
    ).exclude(
        status__in=["cancelled", "returned"]
    )

    # Get the current time in the active timezone
    now = timezone.now()

    if grouping_method == "Daily":
        # Requirement: "Current week days sales"
        # Find the start of the current week (assuming Monday is start)
        start_of_week = now - timedelta(days=now.weekday())
        start_of_week = start_of_week.replace(hour=0, minute=0, second=0, microsecond=0)
        
        # Filter data from the start of the week
        query_set = query_set.filter(order__created_at__gte=start_of_week)
        
        grouping_data = (
            query_set
            .annotate(period=TruncDate("order__created_at"))
            .values("period")
            .annotate(total=Sum("net_paid_amount"))
            .order_by("period")
        )
        date_format = "%Y-%m-%d" # Example: 2026-01-07

    elif grouping_method == "Weekly":
        # Requirement: "Current month week sales"
        # Find the start of the current month
        start_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        
        # Filter data from the start of the month
        query_set = query_set.filter(order__created_at__gte=start_of_month)
        
        grouping_data = (
            query_set
            .annotate(period=TruncWeek("order__created_at"))
            .values("period")
            .annotate(total=Sum("net_paid_amount"))
            .order_by("period")
        )
        date_format = "%Y-%m-%d" # Shows the start date of the week

    elif grouping_method == "Monthly":
        # Requirement: "Months in the current year performance"
        # Find the start of the current year
        start_of_year = now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
        
        # Filter data from the start of the year
        query_set = query_set.filter(order__created_at__gte=start_of_year)
        
        grouping_data = (
            query_set
            .annotate(period=TruncMonth("order__created_at"))
            .values("period")
            .annotate(total=Sum("net_paid_amount"))
            .order_by("period")
        )
        date_format = "%Y-%m" # Example: 2026-01

    elif grouping_method == "Yearly":
        # Requirement: "Yearly sales performance" (Usually implies all time history)
        # No filter applied here, so it calculates sums for every year in the database
        
        grouping_data = (
            query_set
            .annotate(period=TruncYear("order__created_at"))
            .values("period")
            .annotate(total=Sum("net_paid_amount"))
            .order_by("period")
        )
        date_format = "%Y" # Example: 2026

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


