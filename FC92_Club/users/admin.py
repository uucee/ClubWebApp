from django.contrib import admin

# Register your models here.
# users/admin.py
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User
from .models import Profile

# Define an inline admin descriptor for Profile model
# which acts a bit like a singleton
class ProfileInline(admin.StackedInline):
    model = Profile
    can_delete = False
    verbose_name_plural = 'Profile'
    fk_name = 'user'
    fields = ('role', 'status', 'phone_number', 'address', 'join_date')
    readonly_fields = ('join_date',)

# Define a new User admin
class UserAdmin(BaseUserAdmin):
    inlines = (ProfileInline,)
    list_display = ('username', 'email', 'first_name', 'last_name', 'is_staff', 'get_role', 'get_status', 'is_active')
    list_select_related = ('profile',)
    list_filter = ('is_staff', 'is_superuser', 'is_active', 'groups', 'profile__role', 'profile__status') # Filter by role/status

    def get_role(self, instance):
        return instance.profile.get_role_display()
    get_role.short_description = 'Role'

    def get_status(self, instance):
        return instance.profile.get_status_display()
    get_status.short_description = 'Status'

    # Add profile fields to the fieldsets for editing user
    fieldsets = BaseUserAdmin.fieldsets + (
        ('Member Details', {'fields': ()}), # Placeholder, handled by inline
    )
    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        ('Member Details', {'fields': ()}), # Placeholder, handled by inline
    )


# Re-register UserAdmin
admin.site.unregister(User)
admin.site.register(User, UserAdmin)

# Optional: Register Profile directly if needed, but editing via User is often better
# admin.site.register(Profile)
