"""URL patterns for finance app."""
from django.urls import path
from . import views

app_name = "finance"

urlpatterns = [
    # Dashboard
    path("", views.finance_summary, name="finance_summary"),
    path("summary/", views.finance_summary, name="finance_summary"),

    # Dues Tracker
    path("dues/", views.dues_tracker, name="dues_tracker"),
    path("dues/debtors/", views.dues_debtors_list, name="dues_debtors_list"),
    # Smart allocation (replaces old single-year dues_create)
    path("dues/allocate/", views.dues_allocate, name="dues_allocate"),
    # Legacy single-year create (kept for backward compatibility, redirects to allocate)
    path("dues/create/", views.dues_allocate, name="dues_create"),
    path("dues/<int:pk>/delete/", views.dues_delete, name="dues_delete"),
    path("members/<int:member_id>/dues/", views.member_dues_detail, name="member_dues_detail"),

    # Prepaid Dues
    path("prepaid/", views.prepaid_list, name="prepaid_list"),
    path("prepaid/<int:member_id>/", views.prepaid_detail, name="prepaid_detail"),

    # Donations / Contributions
    path("donations/", views.donation_list, name="donation_list"),
    path("donations/create/", views.income_create, name="donation_create"),
    path("donations/<int:pk>/", views.income_detail, name="income_detail"),
    path("donations/<int:pk>/delete/", views.income_delete, name="income_delete"),

    # Legacy Income (redirects to donations)
    path("income/", views.income_list, name="income_list"),
    path("income/create/", views.income_create, name="income_create"),
    path("income/<int:pk>/", views.income_detail, name="income_detail"),
    path("income/<int:pk>/delete/", views.income_delete, name="income_delete"),

    # Expenses
    path("expenses/", views.expense_list, name="expense_list"),
    path("expenses/create/", views.expense_create, name="expense_create"),
    path("expenses/<int:pk>/", views.expense_detail, name="expense_detail"),
    path("expenses/<int:pk>/delete/", views.expense_delete, name="expense_delete"),

    # AJAX
    path("api/search-members/", views.search_members, name="search_members"),
    path("api/member-dues-preview/", views.member_dues_preview, name="member_dues_preview"),
]
