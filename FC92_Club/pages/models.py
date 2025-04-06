from django.db import models

# Create your models here.
# pages/models.py
from django.db import models
from django.conf import settings
from django.utils import timezone

class Announcement(models.Model):
    title = models.CharField(max_length=200)
    content = models.TextField()
    publish_date = models.DateTimeField(default=timezone.now)
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    is_published = models.BooleanField(default=True, help_text="Untick to hide announcement.")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title

    class Meta:
        ordering = ['-publish_date'] # Show newest first