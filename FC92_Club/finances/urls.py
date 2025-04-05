# finances/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('dashboard/', views.financial_dashboard, name='financial_dashboard'),
    path('record-payment/', views.record_payment, name='record_payment'),
    path('manage-dues/', views.manage_dues, name='manage_dues'),

    # Financial Status Views
    path('my-status/', views.member_financial_status, name='my_financial_status'), # For logged-in user's own status
    path('member-status/<int:profile_id>/', views.member_financial_status, name='member_financial_status'), # For FS/Admin viewing specific member

    # Add paths for editing/deleting payments/dues if needed
]