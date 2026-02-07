from django.urls import path
from .views import cases_list, add_case, update_case_status

urlpatterns = [
    path('cases/', cases_list, name='cases_list'),
    path('cases/add/', add_case, name='add_case'),
    path('cases/update/<int:case_id>/', update_case_status, name='update_case_status'),
]
