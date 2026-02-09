from django.urls import path
from .views import taskforce_list, add_taskforce, motorcycles_list, add_motorcycle, edit_taskforce, delete_taskforce, \
    edit_motorcycle, delete_motorcycle

urlpatterns = [
    path('taskforce/', taskforce_list, name='taskforce_list'),
    path('taskforce/add/', add_taskforce, name='add_taskforce'),
    path('motorcycles/', motorcycles_list, name='motorcycles_list'),
    path('motorcycles/add/', add_motorcycle, name='add_motorcycle'),

    path('taskforce/edit/<int:taskforce_id>/', edit_taskforce, name='edit_taskforce'),
    path('taskforce/delete/<int:taskforce_id>/', delete_taskforce, name='delete_taskforce'),

    path('motorcycles/edit/<int:motorcycle_id>/', edit_motorcycle, name='edit_motorcycle'),
    path('motorcycles/delete/<int:motorcycle_id>/', delete_motorcycle, name='delete_motorcycle'),


]
