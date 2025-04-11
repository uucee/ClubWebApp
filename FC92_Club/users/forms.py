# users/forms.py
from django import forms
from django.contrib.auth import get_user_model
from django_countries.fields import CountryField
from django_countries.widgets import CountrySelectWidget

from .models import Profile  #Assuming USER_ROLE_CHOICES is defined in models.py

User = get_user_model()

class ProfileUpdateForm(forms.ModelForm):
    first_name = forms.CharField(max_length=30, required=True)
    last_name = forms.CharField(max_length=30, required=True)
    email = forms.EmailField(required=True)
    middle_name = forms.CharField(max_length=30, required=False)
    phone_number = forms.CharField(max_length=20, required=False)
    address = forms.CharField(widget=forms.Textarea, required=False)
    city = forms.CharField(max_length=100, required=False)
    country = CountryField(blank_label='(Select country)').formfield(
        required=False,
        widget=CountrySelectWidget(attrs={'class': 'form-control'})
    )

    class Meta:
        model = Profile
        fields = ['phone_number', 'address', 'city', 'country']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and hasattr(self.instance, 'user'):
            self.fields['first_name'].initial = self.instance.user.first_name
            self.fields['last_name'].initial = self.instance.user.last_name
            self.fields['email'].initial = self.instance.user.email
            self.fields['middle_name'].initial = self.instance.user.middle_name

    def save(self, commit=True):
        profile = super().save(commit=False)
        user = profile.user
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data['last_name']
        user.email = self.cleaned_data['email']
        user.middle_name = self.cleaned_data['middle_name']
        if commit:
            user.save()
            profile.save()
        return profile

class AdminProfileUpdateForm(ProfileUpdateForm):
    role = forms.ChoiceField(choices=Profile.ROLES, required=True)

    class Meta(ProfileUpdateForm.Meta):
        fields = ProfileUpdateForm.Meta.fields + ['role']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['role'].initial = self.instance.role if self.instance else 'MEM'

class ProfileCompletionForm(forms.ModelForm):
    username = forms.CharField(max_length=150, required=True)
    email = forms.EmailField(required=True)
    password = forms.CharField(widget=forms.PasswordInput, required=True)
    password_confirm = forms.CharField(widget=forms.PasswordInput, required=True)
    first_name = forms.CharField(max_length=150, required=True)
    middle_name = forms.CharField(max_length=30, required=False)
    last_name = forms.CharField(max_length=150, required=True)
    phone_number = forms.CharField(max_length=20, required=False)
    address = forms.CharField(widget=forms.Textarea, required=False)
    city = forms.CharField(max_length=100, required=False)
    country = CountryField(blank_label='(Select country)').formfield(
        required=False,
        widget=CountrySelectWidget(attrs={'class': 'form-control'})
    )

    class Meta:
        model = Profile
        fields = ['phone_number', 'address', 'city', 'country']

    def __init__(self, *args, **kwargs):
        self.user_instance = kwargs.pop('user_instance', None)
        super().__init__(*args, **kwargs)
        
        if self.user_instance:
            self.fields['username'].initial = self.user_instance.username
            self.fields['email'].initial = self.user_instance.email
            self.fields['first_name'].initial = self.user_instance.first_name
            self.fields['last_name'].initial = self.user_instance.last_name
            self.fields['middle_name'].initial = getattr(self.user_instance, 'middle_name', '')

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        password_confirm = cleaned_data.get('password_confirm')

        if password and password_confirm:
            if password != password_confirm:
                raise forms.ValidationError("The passwords don't match.")
        return cleaned_data

    def clean_username(self):
        username = self.cleaned_data.get('username')
        if username:
            # Only check other users, not the current one
            exists = get_user_model().objects.filter(username=username)
            if self.user_instance:
                exists = exists.exclude(pk=self.user_instance.pk)
            
            if exists.exists():
                raise forms.ValidationError("This username is already taken.")
        return username

    def save(self, commit=True):
        profile = super().save(commit=False)
        user = profile.user
        user.username = self.cleaned_data['username']
        user.set_password(self.cleaned_data['password'])
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data['last_name']
        user.middle_name = self.cleaned_data['middle_name']
        if commit:
            user.save()
            profile.save()
        return profile