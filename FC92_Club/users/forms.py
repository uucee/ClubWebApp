# users/forms.py
from django import forms
from .models import Profile

class ProfileUpdateForm(forms.ModelForm):
    first_name = forms.CharField(max_length=30, required=True)
    last_name = forms.CharField(max_length=30, required=True)
    middle_name = forms.CharField(max_length=30, required=False)
    email = forms.EmailField(required=True)
    phone = forms.CharField(max_length=20, required=False)
    address = forms.CharField(widget=forms.Textarea, required=False)
    city = forms.CharField(max_length=100, required=False)
    country = forms.CharField(max_length=100, required=False)
    
    class Meta:
        model = Profile
        fields = ['first_name', 'middle_name', 'last_name', 'email', 'phone', 'address', 'city', 'country']
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and hasattr(self.instance, 'user'):
            self.fields['first_name'].initial = self.instance.user.first_name
            self.fields['last_name'].initial = self.instance.user.last_name
            self.fields['middle_name'].initial = getattr(self.instance.user, 'middle_name', '')
            self.fields['email'].initial = self.instance.user.email
            
    def save(self, commit=True):
        profile = super().save(commit=False)
        if commit:
            profile.user.first_name = self.cleaned_data['first_name']
            profile.user.last_name = self.cleaned_data['last_name']
            profile.user.middle_name = self.cleaned_data['middle_name']
            profile.user.email = self.cleaned_data['email']
            profile.user.save()
            profile.save()
        return profile