"""
URL patterns for members app.
"""
from django.urls import path
from . import views

app_name = "members"

urlpatterns = [
    path("", views.member_list, name="member_list"),
    path("create/", views.member_create, name="member_create"),
    path("<int:pk>/", views.member_detail, name="member_detail"),
    path("<int:pk>/update/", views.member_update, name="member_update"),
    path("<int:pk>/remove/", views.member_remove, name="member_remove"),
    path("<int:pk>/delete/", views.member_delete, name="member_delete"),
    path("clans/", views.clan_list, name="clan_list"),
    path("clans/create/", views.clan_create, name="clan_create"),
    path("api/stats/", views.member_stats_ajax, name="member_stats_ajax"),
    path("api/autocomplete/", views.member_autocomplete_search, name="member_autocomplete_search"),
]
