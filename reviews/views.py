from django.shortcuts import get_object_or_404, redirect, render, redirect
from django.contrib import messages
from orders.models import OrderItem
from .models import ProductReview

def add_review(request, order_item_id):

    if not request.user.is_authenticated or request.user.is_superuser:
        return redirect("user_login")

    order_item = get_object_or_404(
        OrderItem,
        id=order_item_id,
        order__user=request.user,
        status="delivered"
    )

    if hasattr(order_item, "review"):
        messages.error(request, "You already reviewed this product.")
        return redirect("order_detail", order_item.order.uuid)

    errors = {}

    if request.method == "POST":
        rating = request.POST.get("rating", "").strip()
        comment = request.POST.get("comment", "").strip()

        if not rating:
            errors["rating"] = "Rating is required."
        else:
            try:
                rating = int(rating)
                if rating < 1 or rating > 5:
                    errors["rating"] = "Rating must be between 1 and 5."
            except ValueError:
                errors["rating"] = "Invalid rating value."

        if not comment:
            errors["comment"] = "Comment is required."
        elif len(comment) < 5:
            errors["comment"] = "Comment must be at least 5 characters."
        elif len(comment) > 500:
            errors["comment"] = "Comment cannot exceed 500 characters."

        if errors:
            return render(
                request,
                "reviews/add_review.html",
                {
                    "item": order_item,
                    "errors": errors,
                    "rating": request.POST.get("rating"),
                    "comment": request.POST.get("comment"),
                }
            )

        ProductReview.objects.create(
            user=request.user,
            product=order_item.product,
            order_item=order_item,
            rating=rating,
            comment=comment
        )

        messages.success(request, "Review submitted successfully.")
        return redirect("order_detail", order_item.order.uuid)

    return render(request, "reviews/add_review.html", {"item": order_item})



