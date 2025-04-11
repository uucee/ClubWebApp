from django.db.models.signals import post_save
from django.dispatch import receiver
from django.conf import settings
from .models import Profile

@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_or_update_user_profile(sender, instance, created, **kwargs):
    """
    Create a profile for a new user, or ensure existing user has one.
    Uses get_or_create to be robust.
    """
    if created:
        Profile.objects.get_or_create(user=instance)
    else:
        # Ensure profile exists for existing users, in case it was missed
        # or if you add profile fields that need saving when user saves.
        # Often instance.profile.save() is called here, but get_or_create
        # handles the creation case safely.
        Profile.objects.get_or_create(user=instance)

# Optional: If you need to save profile changes when the user is saved
# @receiver(post_save, sender=settings.AUTH_USER_MODEL)
# def save_user_profile(sender, instance, **kwargs):
#    try:
#        instance.profile.save()
#    except Profile.DoesNotExist:
        # Should be handled by create_or_update_user_profile
#        pass