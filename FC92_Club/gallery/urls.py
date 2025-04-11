from django.urls import path
from . import views

app_name = 'gallery'

urlpatterns = [
    path('', views.event_list, name='event_list'),
    path('event/<int:pk>/', views.event_detail, name='event_detail'),
    path('event/create/', views.event_create, name='event_create'),
    path('event/<int:pk>/edit/', views.event_edit, name='event_edit'),
    path('event/<int:pk>/delete/', views.event_delete, name='event_delete'),
    path('event/<int:event_pk>/photos/upload/', views.photo_upload, name='photo_upload'),
    path('photo/<int:pk>/edit/', views.photo_edit, name='photo_edit'),
    path('photo/<int:pk>/delete/', views.photo_delete, name='photo_delete'),
] 