# users/urls.py
from django.urls import path
from . import views

app_name = 'users'

urlpatterns = [
    # Profile URLs
    path('profile/edit/', views.profile_edit, name='profile_edit'),
    path('profile/<str:username>/edit/', views.profile_edit, name='profile_edit_other'),
    path('profile/', views.profile_view, name='profile_view'),
    path('profile/<str:username>/', views.profile_view, name='profile'),

    # Admin/FS URLs
    path('admin/members/', views.member_list, name='member_list'),
    path('admin/members/<int:user_id>/financial/', views.member_financial_detail, name='member_financial_detail'),
    path('admin/members/<int:profile_id>/status/', views.update_member_status, name='update_member_status'),
    path('admin/members/<int:user_id>/toggle/', views.toggle_member_access, name='toggle_member_access'),
    path('admin/members/<int:user_id>/delete/', views.delete_member, name='delete_member'),
    path('admin/members/management/', views.member_management, name='member_management'),
    path('admin/members/add/', views.add_single_member, name='add_single_member'),
    path('admin/members/bulk-upload/', views.bulk_upload_members, name='bulk_upload_members'),
    path('admin/members/send-invites/', views.send_bulk_invites, name='send_bulk_invites'),
    path('admin/members/financial-report/', views.financial_report, name='financial_report'),

    # Admin password reset
    path('admin/reset-password/<int:user_id>/', views.admin_reset_password, name='admin_reset_password'),

    # Invitation URLs
    path('accept-invitation/<str:token>/', views.accept_invitation, name='accept_invitation'),
]