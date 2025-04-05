# finances/forms.py
from django import forms
from .models import Payment, Due
from users.models import Profile # To populate member choices

class PaymentForm(forms.ModelForm):
    # If FS needs to select member when recording payment
    member = forms.ModelChoiceField(
        queryset=Profile.objects.filter(status=Profile.Status.ACTIVE).select_related('user').order_by('user__username'),
        label="Member"
    )

    class Meta:
        model = Payment
        fields = ['member', 'amount_paid', 'payment_date', 'notes']
        widgets = {
            'payment_date': forms.DateInput(attrs={'type': 'date'}), # HTML5 date picker
        }

class DueForm(forms.ModelForm):
    # Allow selecting multiple members to apply a due to? More complex.
    # Single member selection for now:
    member = forms.ModelChoiceField(
        queryset=Profile.objects.filter(status=Profile.Status.ACTIVE).select_related('user').order_by('user__username'),
        label="Member",
        required=True
    )
    
    class Meta:
        model = Due
        fields = ['member', 'amount_due', 'description', 'due_date']
        widgets = {
            'due_date': forms.DateInput(attrs={'type': 'date'}),
            'amount_due': forms.NumberInput(attrs={'step': '0.01'}),
        }
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Add any additional initialization here if needed

# Form to apply a Due to *all* active members (e.g., annual fee)
class BulkDueForm(forms.Form):
    amount_due = forms.DecimalField(max_digits=8, decimal_places=2)
    description = forms.CharField(max_length=255)
    due_date = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}))