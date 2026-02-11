from django.conf import settings
from django.urls import path

from . import views
from .views import login_view, logout_view, dashboard, admin_dashboard, members_list, tenures_list, add_member, \
    add_tenure, delete_tenure, edit_tenure, announcements_list, add_announcement, edit_announcement, delete_announcement
from .views import member_profile
from .views import executives_list, assign_executive
from django.conf.urls.static import static

urlpatterns = [
    path('login/', login_view, name='login'),
    path('logout/', logout_view, name='logout'),
    path('dashboard/', dashboard, name='dashboard'),
    path('admin-dashboard/', admin_dashboard, name='admin_dashboard'),
    path('members/', members_list, name='members_list'),
    path('members/<int:member_id>/', member_profile, name='member_profile'),
    path('tenure/add/', add_tenure, name='add_tenure'),
    path('tenures/', tenures_list, name='tenures_list'),
    path('tenures/<int:tenure_id>/edit/', edit_tenure, name='edit_tenure'),
    path('tenures/<int:tenure_id>/delete/', delete_tenure, name='delete_tenure'),

    path('executives/', executives_list, name='executives_list'),
    path('executives/assign/', assign_executive, name='assign_executive'),
    path('members/add/', add_member, name='add_member'),
    path('members/edit/<int:member_id>/', views.edit_member, name='edit_member'),
    path('members/delete/<int:member_id>/', views.delete_member, name='delete_member'),

    path('announcements/', announcements_list, name='announcements_list'),
    path('announcements/add/', add_announcement, name='add_announcement'),
    path('announcements/edit/<int:announcement_id>/', edit_announcement, name='edit_announcement'),
    path('announcements/delete/<int:announcement_id>/', delete_announcement, name='delete_announcement'),

    path('minutes/', views.minutes_list, name='minutes_list'),
    path('minutes/add/', views.add_minutes, name='add_minutes'),
    path('minutes/edit/<int:minutes_id>/', views.edit_minutes, name='edit_minutes'),
    path('minutes/delete/<int:minutes_id>/', views.delete_minutes, name='delete_minutes'),
    path('executive/edit/<int:executive_id>/', views.edit_executive, name='edit_executive'),
    path('executive/delete/<int:executive_id>/', views.delete_executive, name='delete_executive'),

]
urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
