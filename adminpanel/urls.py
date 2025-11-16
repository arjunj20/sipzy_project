from django.urls import path
from . import views


urlpatterns = [

    path("admin-dashboard/", views.admin_dashboard, name="admin_dashboard"),
    path("admin-login/", views.admin_login, name="admin_login"),
    path("admin-logout/", views.admin_logout, name="admin_logout"),
    path("category-list/", views.category_list, name="category_list"),
    path("category-add/", views.category_add, name="category_add"),
    path("category-delete/<int:id>/", views.category_delete, name="category_delete"),
    path("category-edit/<int:id>/", views.category_edit, name="category_edit"),


]