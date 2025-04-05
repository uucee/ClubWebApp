# users/forms.py
from django import forms
from .models import Profile

class ProfileUpdateForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = ['phone_number', 'address'] # Only fields members can edit themselves
        # Add widgets if desired e.g., forms.Textarea for address