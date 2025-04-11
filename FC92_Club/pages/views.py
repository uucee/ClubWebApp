# Create your views here.
# pages/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.utils import timezone
from .models import Announcement
from .forms import AnnouncementForm

def home_page(request):
    announcements = Announcement.objects.filter(
        is_published=True,
        publish_date__lte=timezone.now() # Only show published and past/current publish date
    ).order_by('-publish_date')[:5] # Show latest 5

    context = {
        'announcements': announcements
    }
    return render(request, 'pages/home.html', context)

@login_required
@user_passes_test(lambda u: u.profile.role == 'ADM')
def create_announcement(request):
    """Create a new announcement."""
    if request.method == 'POST':
        form = AnnouncementForm(request.POST)
        if form.is_valid():
            announcement = form.save(commit=False)
            announcement.author = request.user
            announcement.save()
            messages.success(request, 'Announcement created successfully.')
            return redirect('pages:announcement_list')
    else:
        form = AnnouncementForm()
    
    return render(request, 'pages/announcement_form.html', {'form': form})

@login_required
def announcement_list(request):
    """List all active announcements."""
    announcements = Announcement.objects.filter(
        is_published=True,
        publish_date__lte=timezone.now()
    ).order_by('-publish_date')
    is_admin = request.user.profile.role == 'ADM' if hasattr(request.user, 'profile') else False
    
    return render(request, 'pages/announcement_list.html', {
        'announcements': announcements,
        'is_admin': is_admin
    })

@login_required
@user_passes_test(lambda u: u.profile.role == 'ADM')
def toggle_announcement(request, announcement_id):
    """Toggle announcement published status."""
    announcement = get_object_or_404(Announcement, id=announcement_id)
    announcement.is_published = not announcement.is_published
    announcement.save()
    
    status = "published" if announcement.is_published else "unpublished"
    messages.success(request, f'Announcement has been {status}.')
    return redirect('pages:announcement_list')
