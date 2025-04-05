# Register your models here.
# pages/admin.py
from django.contrib import admin
from .models import Announcement

@admin.register(Announcement)
class AnnouncementAdmin(admin.ModelAdmin):
    list_display = ('title', 'publish_date', 'author', 'is_published', 'updated_at')
    list_filter = ('is_published', 'author', 'publish_date')
    search_fields = ('title', 'content')
    date_hierarchy = 'publish_date'
    # Automatically set author if not set
    def save_model(self, request, obj, form, change):
        if not obj.author_id:
             obj.author = request.user
        super().save_model(request, obj, form, change)
    # Consider adding prepopulated_fields for slug if you add one later for blog posts