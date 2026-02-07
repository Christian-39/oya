from django.conf import settings
from django.urls import path
from .views import login_view, logout_view, dashboard, admin_dashboard, members_list, tenures_list, add_member, \
    add_tenure, delete_tenure, edit_tenure
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
]
urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
