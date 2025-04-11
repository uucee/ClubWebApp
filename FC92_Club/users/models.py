from django.db import models
from django.contrib.auth.models import AbstractUser
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone
from django_countries.fields import CountryField


class User(AbstractUser):
    middle_name = models.CharField(max_length=30, blank=True)
    
    # Add related_name to avoid clashes with auth.User
    groups = models.ManyToManyField(
        'auth.Group',
        related_name='custom_user_set',
        blank=True,
        help_text='The groups this user belongs to. A user will get all permissions granted to each of their groups.',
        verbose_name='groups',
    )
    user_permissions = models.ManyToManyField(
        'auth.Permission',
        related_name='custom_user_set',
        blank=True,
        help_text='Specific permissions for this user.',
        verbose_name='user permissions',
    )
    
    def get_full_name(self):
        """Return the full name including middle name if available."""
        name_parts = [self.first_name]
        if self.middle_name:
            name_parts.append(self.middle_name)
        name_parts.append(self.last_name)
        return ' '.join(name_parts)

    def get_short_name(self):
        """Return the short name for the user."""
        return self.first_name

    @property
    def is_financial_secretary(self):
        """Check if user is a financial secretary."""
        return hasattr(self, 'profile') and self.profile.is_financial_secretary

    @property
    def is_admin(self):
        """Check if user is an admin."""
        return hasattr(self, 'profile') and self.profile.is_admin

    def has_perm(self, perm, obj=None):
        """Override to check admin status."""
        if self.is_admin or self.is_superuser:
            return True
        return super().has_perm(perm, obj)

    def has_module_perms(self, app_label):
        """Override to check admin status."""
        if self.is_admin or self.is_superuser:
            return True
        return super().has_module_perms(app_label)

    class Meta:
        verbose_name = 'user'
        verbose_name_plural = 'users'

class Profile(models.Model):
        # filepath: c:\Django Project\FC92_Club\FC92_Club\users\models.py
    # ... other imports ...
    
    # Define choices for the role field
    ROLES = [
        ('ADM', 'Admin'),
        ('FS', 'Financial Secretary'),
        ('MEM', 'Member'),
    ]
    
    # ... rest of the file, including Profile class ...

    STATUS_CHOICES = (
        ('ACT', 'Active'),
        ('SUS', 'Suspended'),
        ('REM', 'Removed'),
    )

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    role = models.CharField(max_length=3, choices=ROLES, default='MEM')
    status = models.CharField(max_length=3, choices=STATUS_CHOICES, default='ACT')
    phone_number = models.CharField(max_length=20, blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    city = models.CharField(max_length=100, blank=True, null=True)
    country = CountryField(blank=True, null=True)
    invitation_token = models.CharField(max_length=32, blank=True, null=True)
    invitation_sent_at = models.DateTimeField(blank=True, null=True)

    def __str__(self):
        return f"{self.user.get_full_name()} ({self.get_role_display()})"

    @property
    def is_admin(self):
        return self.role == 'ADM'

    @property
    def is_financial_secretary(self):
        return self.role == 'FS'

    @property
    def is_active_member(self):
        # Checks both user active status and profile status
        return self.user.is_active and self.status == 'ACT'

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

    class Meta:
        ordering = ['user__last_name', 'user__first_name']

# Signal to create or update Profile when User is created/saved
@receiver(post_save, sender=User)
def create_or_update_user_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)
    else:
        instance.profile.save()
