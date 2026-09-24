"""
URL patterns for elections app.
"""
from django.urls import path
from . import views

app_name = "elections"

urlpatterns = [
    path("", views.election_list, name="election_list"),
    path("create/", views.election_create, name="election_create"),
    path("<int:pk>/", views.election_detail, name="election_detail"),
    path("<int:pk>/update/", views.election_update, name="election_update"),
    path("candidates/create/", views.candidate_create, name="candidate_create"),
    path("candidates/<int:pk>/update/", views.candidate_update, name="candidate_update"),
    path("candidate/<int:pk>/vote/", views.cast_vote, name="cast_vote"),
    
    # Handover Ledger URLs
    path("handovers/", views.handover_list, name="handover_list"),
    path("handovers/create/", views.handover_create, name="handover_create"),
    path("handovers/<int:pk>/", views.handover_detail, name="handover_detail"),
    path("handovers/<int:pk>/update/", views.handover_update, name="handover_update"),
    path("handovers/<int:pk>/delete/", views.handover_delete, name="handover_delete"),

    # Executive Handover Report URLs
    path("administrations/", views.administration_list, name="administration_list"),
    path("administrations/<str:key>/", views.administration_report, name="administration_report"),
]
