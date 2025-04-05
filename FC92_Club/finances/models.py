

# Create your models here.
# finances/models.py
from django.db import models
from django.contrib.auth.models import User
from users.models import Profile # Import Profile
from decimal import Decimal

class Due(models.Model):
    member = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name='dues')
    amount_due = models.DecimalField(max_digits=8, decimal_places=2)
    description = models.CharField(max_length=255)
    due_date = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.description} for {self.member.user.username} due {self.due_date}"

class Payment(models.Model):
    member = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name='payments')
    amount_paid = models.DecimalField(max_digits=8, decimal_places=2)
    payment_date = models.DateField()
    notes = models.TextField(blank=True, null=True)
    recorded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='recorded_payments')
    recorded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Payment of {self.amount_paid} by {self.member.user.username} on {self.payment_date}"
