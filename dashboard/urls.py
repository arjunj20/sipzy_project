from django.urls import path
from . import views

urlpatterns = [

        path("admin-dashboard/", views.admin_dashboard, name="admin_dashboard"),
        path("visualization-data/", views.visualization_data, name="visualization_data"),


]