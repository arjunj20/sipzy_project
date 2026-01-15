from django.urls import path
from . import views


urlpatterns = [

    path("", views.admin_login, name="admin_login"),
    path("admin-logout/", views.admin_logout, name="admin_logout"),
    path("inventory/", views.admin_inventory, name="admin_inventory"),
    path("category-list/", views.category_list, name="category_list"),
    path("category-add/", views.category_add, name="category_add"),
    path("category-delete/<int:id>/", views.category_delete, name="category_delete"),
    path("category-edit/<int:id>/", views.category_edit, name="category_edit"),
    path("user-block/<int:id>/", views.block_user, name="block_user"),
    path("user-unblock/<int:id>/", views.unblock_user, name="unblock_user"),
    path("user-list/", views.user_list, name="user_list"),
    path("brand-list/", views.brand_list, name="brand_list"),
    path("brand-add/", views.brand_add, name="brand_add"),
    path("brand-edit/<int:id>/", views.brand_edit, name="brand_edit"),
    path("brand-delete/<int:id>/", views.brand_delete, name="brand_delete"),
    path("product-list/", views.product_list, name="product_list"),
    path("product-delete/<int:product_id>/", views.product_delete, name="product_delete"),

    path("product-create/", views.product_create, name="product_create"),
    path("product-edit/<uuid:uuid>/", views.product_edit, name="product_edit"),

    path("variants/<uuid:uuid>/delete/", views.variant_delete, name="variant_delete"),

    path("images/<int:image_id>/delete/", views.product_image_delete, name="product_image_delete"),


    path("order-items/", views.admin_order_item_list, name="admin_order_item_list"),
    path("order-details/<uuid:uuid>/", views.admin_order_item_detail, name="admin_order_item_detail"),
    path("order-update/<int:item_id>/update/", views.update_suborder_status, name="update_suborder_status"),
    path(
        'variant-list/<uuid:product_uuid>/',
        views.admin_variant_list,
        name='variant_list'
        ),
    
    path("admin/variants/edit/<uuid:uuid>/", views.admin_edit_variant, name="edit_variant"),

    path(
        "sales-report/",
        views.admin_sales_report,
        name="admin_sales_report"
    ),

    path(
        "sales-report/excel/",
        views.sales_report_excel,
        name="sales_report_excel"
    ),

    path(
        "sales-report/pdf/",
        views.sales_report_pdf,
        name="sales_report_pdf")
]   