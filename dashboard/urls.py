"""
URL patterns for dashboard app.
"""
from django.urls import path
from . import views

app_name = "dashboard"

urlpatterns = [
    path("", views.index, name="index"),
    path('member/', views.member_dashboard, name='member_dashboard'),
    path("admin/", views.admin_dashboard, name="admin_dashboard"),
    path('search/api/', views.global_search_ajax, name='global_search_ajax'),
    path('financial-trend/ajax/', views.financial_trend_ajax, name='financial_trend_ajax'),
]
