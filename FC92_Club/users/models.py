from django.db import models
from django.contrib.auth.models import AbstractUser
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone

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
    phone = models.CharField(max_length=20, blank=True)
    address = models.TextField(blank=True)
    city = models.CharField(max_length=100, blank=True)
    country = models.CharField(max_length=100, blank=True)
    role = models.CharField(max_length=3, choices=Role.choices, default=Role.MEMBER)
    status = models.CharField(max_length=3, choices=Status.choices, default=Status.PENDING)
    invitation_token = models.CharField(max_length=32, blank=True, null=True)
    invitation_sent_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.user.get_full_name()} ({self.get_role_display()})"

    def get_full_name(self):
        """Return the full name including middle name if available."""
        name_parts = [self.user.first_name]
        if hasattr(self, 'middle_name') and self.middle_name:
            name_parts.append(self.middle_name)
        name_parts.append(self.user.last_name)
        return ' '.join(name_parts)

    @property
    def is_financial_secretary(self):
        """Check if user is a financial secretary."""
        return self.role == self.Role.FINANCIAL_SECRETARY

    @property
    def is_admin(self):
        """Check if user is an admin."""
        return self.role == self.Role.ADMIN

    @property
    def is_active_member(self):
        # Checks both user active status and profile status
        return self.user.is_active and self.status == self.Status.ACTIVE

    def save(self, *args, **kwargs):
        if not self.created_at:
            self.created_at = timezone.now()
        self.updated_at = timezone.now()
        super().save(*args, **kwargs)

# Signal to create or update Profile when User is created/saved
#@receiver(post_save, sender=User)
#def create_or_update_user_profile(sender, instance, created, **kwargs):
#    if created:
#        Profile.objects.get_or_create(user=instance)
    #instance.profile.save()
