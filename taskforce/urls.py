from django.urls import path
from .views import taskforce_list, add_taskforce, motorcycles_list, add_motorcycle

urlpatterns = [
    path('taskforce/', taskforce_list, name='taskforce_list'),
    path('taskforce/add/', add_taskforce, name='add_taskforce'),
    path('motorcycles/', motorcycles_list, name='motorcycles_list'),
    path('motorcycles/add/', add_motorcycle, name='add_motorcycle'),
]
