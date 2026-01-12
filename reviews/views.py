from django.shortcuts import render
from django.shortcuts import get_object_or_404, redirect, render
from django.contrib import messages
from orders.models import OrderItem
from .models import ProductReview

def add_review(request, order_item_id):
    order_item = get_object_or_404(
        OrderItem,
        id=order_item_id,
        order__user=request.user,
        status="delivered"
    )

    if hasattr(order_item, "review"):
        messages.error(request, "You already reviewed this product")
        return redirect("order_details", order_item.order.id)

    if request.method == "POST":
        ProductReview.objects.create(
            user=request.user,
            product=order_item.product,
            order_item=order_item,
            rating=request.POST["rating"],
            comment=request.POST["comment"]
        )
        messages.success(request, "Review submitted successfully")
        return redirect("order_detail", order_item.order.uuid)

    return render(request, "reviews/add_review.html", {"item": order_item})


