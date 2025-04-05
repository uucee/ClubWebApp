from django.db import models

# Create your models here.
# users/models.py
from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver

class Profile(models.Model):
    class Role(models.TextChoices):
        ADMIN = 'ADM', 'Administrator'
        FINANCIAL_SECRETARY = 'FS', 'Financial Secretary'
        MEMBER = 'MEM', 'Member'

    class Status(models.TextChoices):
        ACTIVE = 'ACT', 'Active'
        SUSPENDED = 'SUS', 'Suspended' # Financially not up to date
        REMOVED = 'REM', 'Removed'   # No longer a member
        PENDING = 'PEN', 'Pending'   # Invitation sent but not yet completed profile

    user = models.OneToOneField(User, on_delete=models.CASCADE)
    role = models.CharField(max_length=3, choices=Role.choices, default=Role.MEMBER)
    status = models.CharField(max_length=3, choices=Status.choices, default=Status.PENDING)
    phone_number = models.CharField(max_length=20, blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    join_date = models.DateField(auto_now_add=True)
    invitation_token = models.CharField(max_length=32, blank=True, null=True)
    invitation_sent_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.user.username}'s Profile ({self.get_role_display()})"

    # Convenience properties for permission checks in templates/views
    @property
    def is_admin(self):
        return self.role == self.Role.ADMIN

    @property
    def is_financial_secretary(self):
        return self.role in [self.Role.ADMIN, self.Role.FINANCIAL_SECRETARY]

    @property
    def is_active_member(self):
        # Checks both user active status and profile status
        return self.user.is_active and self.status == self.Status.ACTIVE

# Signal to create or update Profile when User is created/saved
#@receiver(post_save, sender=User)
#def create_or_update_user_profile(sender, instance, created, **kwargs):
#    if created:
#        Profile.objects.get_or_create(user=instance)
    #instance.profile.save()
