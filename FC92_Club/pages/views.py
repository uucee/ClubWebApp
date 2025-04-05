
# Create your views here.
# pages/views.py
from django.shortcuts import render
from .models import Announcement
from django.utils import timezone

def home_page(request):
    announcements = Announcement.objects.filter(
        is_published=True,
        publish_date__lte=timezone.now() # Only show published and past/current publish date
    ).order_by('-publish_date')[:5] # Show latest 5

    context = {
        'announcements': announcements
    }
    return render(request, 'pages/home.html', context)
