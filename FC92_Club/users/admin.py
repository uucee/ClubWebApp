from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import Profile, User

# Define an inline admin descriptor for Profile model
# which acts a bit like a singleton
class ProfileInline(admin.StackedInline):
    model = Profile
    can_delete = False
    verbose_name_plural = 'Profile'
    fk_name = 'user'

# Define a custom User admin
class CustomUserAdmin(BaseUserAdmin):
    inlines = (ProfileInline,)
    list_display = ('username', 'email', 'first_name', 'middle_name', 'last_name', 'is_staff', 'get_role')
    list_select_related = ('profile',)
    fieldsets = BaseUserAdmin.fieldsets + (
        ('Additional Info', {'fields': ('middle_name',)}),
    )
    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        ('Additional Info', {'fields': ('middle_name',)}),
    )

    def get_role(self, instance):
        return instance.profile.get_role_display()
    get_role.short_description = 'Role'

    def get_inline_instances(self, request, obj=None):
        if not obj:
            return list()
        return super(CustomUserAdmin, self).get_inline_instances(request, obj)

# Register the custom User model with our CustomUserAdmin
admin.site.register(User, CustomUserAdmin)

# Optional: Register Profile directly if needed, but editing via User is often better
# admin.site.register(Profile)
