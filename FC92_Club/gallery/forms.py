from django import forms
from .models import Event, Photo

class EventForm(forms.ModelForm):
    class Meta:
        model = Event
        fields = ['title', 'description', 'date']
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date'}),
        }

class PhotoForm(forms.ModelForm):
    class Meta:
        model = Photo
        fields = ['event', 'image', 'caption']

# Form specifically for uploading multiple photos to an existing event
class PhotoUploadForm(forms.Form):
    event = forms.ModelChoiceField(queryset=Event.objects.all(), widget=forms.HiddenInput())
    images = forms.FileField(
        widget=forms.ClearableFileInput(attrs={'allow_multiple_selected': True}),
        required=True,
        label='Select photos'
    )
    captions = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 4}),
        required=False,
        label='Captions (one per line, matching photo order)',
        help_text="Enter one caption per line. They will be matched to the uploaded photos in order."
    )

    def __init__(self, *args, **kwargs):
        event_instance = kwargs.pop('event_instance', None)
        super().__init__(*args, **kwargs)
        if event_instance:
            self.fields['event'].initial = event_instance