# pages/urls.py
# Not strictly needed if only home page is defined at project level,
# but good practice if more static pages are added later.
from django.urls import path
from . import views

app_name = 'pages'

# If you want '/announcements/' page later:
# urlpatterns = [
#    path('announcements/', views.announcement_list, name='announcement_list'),
# ]
urlpatterns = [
    path('', views.home_page, name='home'),
    path('announcements/', views.announcement_list, name='announcement_list'),
    path('announcements/create/', views.create_announcement, name='create_announcement'),
    path('announcements/<int:announcement_id>/toggle/', views.toggle_announcement, name='toggle_announcement'),
]