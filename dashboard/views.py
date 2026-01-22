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

from django.shortcuts import render, redirect
from django.http import JsonResponse
from orders.models import Order, OrderItem 
from django.db.models.functions import TruncDate, TruncMonth, TruncYear, TruncWeek
from django.db.models import Sum
from django.utils import timezone
from datetime import timedelta


@never_cache
def admin_dashboard(request):
    if not request.user.is_authenticated or not request.user.is_superuser:
        return redirect('admin_login')
    users_count = CustomUser.objects.aggregate(count=Count("fullname"))

    total_orders = Order.objects.aggregate(order_count=Count("uuid"))
    top_selling_products = OrderItem.objects.exclude(status__in=['cancelled', 'returned']).values('product__name').annotate(total_sold=Sum('quantity')).order_by('-total_sold')[:10]
    top_selling_categories = OrderItem.objects.exclude(status__in=["cancelled", "returned"]).values("product__category__name").annotate(total_sold=Sum("quantity")).order_by("-total_sold")[:11]
    top_selling_brands = OrderItem.objects.exclude(status__in=["cancelled", "returned"]).values("product__brand__name").annotate(total_sold=Sum("quantity")).order_by("-total_sold")[:10]
    revenue = Order.objects.filter(payment_status="paid", total__gt=0).aggregate(sums=Sum("total"))
    
        
    context = {
        "total_users": users_count['count'],
        "total_orders": total_orders["order_count"],
        "top_selling_products": top_selling_products,
        "top_selling_categories": top_selling_categories,
        "top_selling_brands": top_selling_brands,
        "revenue": revenue,     

    }
    
    return render(request, "dashboard/admin_dashboard.html", context)


def visualization_data(request):
    if not request.user.is_authenticated or not request.user.is_superuser:
        return redirect("admin_login")

    grouping_method = request.GET.get("grouping_method", "Daily")
    now = timezone.now()

    # ✅ SAME SOURCE OF TRUTH
    query_set = Order.objects.filter(payment_status="paid")

    if grouping_method == "Daily":
        start_of_week = now - timedelta(days=now.weekday())
        start_of_week = start_of_week.replace(hour=0, minute=0, second=0, microsecond=0)

        query_set = query_set.filter(created_at__gte=start_of_week)

        grouping_data = (
            query_set
            .annotate(period=TruncDate("created_at"))
            .values("period")
            .annotate(total=Sum("total"))
            .order_by("period")
        )
        date_format = "%Y-%m-%d"

    elif grouping_method == "Weekly":
        start_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        query_set = query_set.filter(created_at__gte=start_of_month)

        grouping_data = (
            query_set
            .annotate(period=TruncWeek("created_at"))
            .values("period")
            .annotate(total=Sum("total"))
            .order_by("period")
        )
        date_format = "%Y-%m-%d"

    elif grouping_method == "Monthly":
        start_of_year = now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
        query_set = query_set.filter(created_at__gte=start_of_year)

        grouping_data = (
            query_set
            .annotate(period=TruncMonth("created_at"))
            .values("period")
            .annotate(total=Sum("total"))
            .order_by("period")
        )
        date_format = "%Y-%m"

    elif grouping_method == "Yearly":
        grouping_data = (
            query_set
            .annotate(period=TruncYear("created_at"))
            .values("period")
            .annotate(total=Sum("total"))
            .order_by("period")
        )
        date_format = "%Y"

    else:
        return JsonResponse({"error": "Invalid grouping method"}, status=400)

    data = [
        {
            "label": row["period"].strftime(date_format),
            "value": float(row["total"] or 0)
        }
        for row in grouping_data
        if row["period"]
    ]

    return JsonResponse({
        "grouping": grouping_method,
        "data": data
    })

