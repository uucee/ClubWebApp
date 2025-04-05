# users/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('profile/', views.profile_view, name='profile_view'),
    path('profile/edit/', views.profile_edit, name='profile_edit'),

    # Admin/FS paths
    path('admin/members/', views.member_list, name='member_list_admin'),
    path('admin/members/<int:user_id>/toggle-access/', views.toggle_member_access, name='toggle_member_access'),
    path('admin/members/<int:user_id>/finances/', views.member_financial_detail, name='member_financial_detail_fs'),
    path('admin/members/profile/<int:profile_id>/update-status/', views.update_member_status, name='update_member_status'),

    # Member Management URLs
    path('admin/members/manage/', views.member_management, name='member_management'),
    path('admin/members/add/', views.add_single_member, name='add_single_member'),
    path('admin/members/bulk-upload/', views.bulk_upload_members, name='bulk_upload_members'),
    path('admin/members/send-invites/', views.send_bulk_invites, name='send_bulk_invites'),

    # Invitation URLs
    path('accept-invitation/<str:token>/', views.accept_invitation, name='accept_invitation'),
]