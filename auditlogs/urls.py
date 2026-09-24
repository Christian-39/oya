"""
URL configuration for auditlogs app.
"""
from django.urls import path
from . import views

app_name = "auditlogs"

urlpatterns = [
    path("", views.auditlog_list, name="auditlog_list"),
    path("<int:pk>/detail/", views.auditlog_detail, name="detail"),
    path("export/", views.auditlog_export, name="export"),
]