"""
URL patterns for operations app.
"""
from django.urls import path
from . import views

app_name = "operations"

urlpatterns = [
    path("taskforce/", views.taskforce_list, name="taskforce_list"),
    path("taskforce/create/", views.taskforce_create, name="taskforce_create"),
    path("taskforce/<int:pk>/update/", views.taskforce_update, name="taskforce_update"),
    path("taskforce/<int:pk>/remove/", views.taskforce_remove, name="taskforce_remove"),
    path("motorcycles/", views.motorcycle_list, name="motorcycle_list"),
    path("motorcycles/create/", views.motorcycle_create, name="motorcycle_create"),
    path("motorcycles/<int:pk>/update/", views.motorcycle_update, name="motorcycle_update"),
    path("motorcycles/<int:pk>/delete/", views.motorcycle_delete, name="motorcycle_delete"),
    path("cases/", views.case_list, name="case_list"),
    path("cases/create/", views.case_create, name="case_create"),
    path("cases/<int:pk>/", views.case_detail, name="case_detail"),
    path("cases/<int:pk>/resolve/", views.case_resolve, name="case_resolve"),
    path("cases/<int:pk>/edit/", views.case_update, name="case_update"),
    path("cases/<int:pk>/delete/", views.case_delete, name="case_delete"),

]
