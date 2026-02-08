from django.urls import path
from . import views

urlpatterns = [
    path('projects/', views.projects_list, name='projects_list'),
    path('project/add/', views.add_project, name='add_project'),
    path('<int:project_id>/', views.project_detail, name='project_detail'),
]
