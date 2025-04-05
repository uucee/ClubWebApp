# pages/urls.py
# Not strictly needed if only home page is defined at project level,
# but good practice if more static pages are added later.
from django.urls import path
from . import views

# If you want '/announcements/' page later:
# urlpatterns = [
#    path('announcements/', views.announcement_list, name='announcement_list'),
# ]
urlpatterns = [] # Empty for now