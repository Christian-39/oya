"""
URL patterns for settingsapp.
"""
from django.urls import path
from . import views

app_name = "settingsapp"

urlpatterns = [
    path("", views.settings_view, name="settings"),

    # Donation Groups (Feature 1, 2, 3)
    path("donation-groups/", views.donation_group_list, name="donation_group_list"),
    path("donation-groups/create/", views.donation_group_create, name="donation_group_create"),
    path("donation-groups/<int:pk>/", views.donation_group_detail, name="donation_group_detail"),
    path("donation-groups/<int:pk>/update/", views.donation_group_update, name="donation_group_update"),
    path("donation-groups/<int:pk>/delete/", views.donation_group_delete, name="donation_group_delete"),
    path("donation-groups/<int:pk>/toggle-active/", views.donation_group_toggle_active, name="donation_group_toggle_active"),
    path("donation-groups/<int:pk>/members/add/", views.donation_group_member_add, name="donation_group_member_add"),
    path("donation-groups/<int:pk>/members/<int:membership_pk>/remove/", views.donation_group_member_remove, name="donation_group_member_remove"),
]
