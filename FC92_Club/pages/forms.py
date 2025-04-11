from django import forms
from .models import Announcement

class AnnouncementForm(forms.ModelForm):
    class Meta:
        model = Announcement
        fields = ['title', 'content', 'publish_date', 'is_published']
        widgets = {
            'content': forms.Textarea(attrs={'rows': 4}),
            'publish_date': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
        } 