# Register your models here.
# finances/admin.py
from django.contrib import admin
from .models import Due, Payment

@admin.register(Due)
class DueAdmin(admin.ModelAdmin):
    list_display = ('member_username', 'description', 'amount_due', 'due_date', 'created_at')
    list_filter = ('due_date', 'member__user__username') # Filter by username via profile
    search_fields = ('description', 'member__user__username', 'member__user__first_name', 'member__user__last_name')
    date_hierarchy = 'due_date'

    def member_username(self, obj):
        return obj.member.user.username
    member_username.short_description = 'Member'


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('member_username', 'amount_paid', 'payment_date', 'recorded_by_username', 'recorded_at')
    list_filter = ('payment_date', 'member__user__username', 'recorded_by')
    search_fields = ('notes', 'member__user__username', 'member__user__first_name', 'member__user__last_name')
    date_hierarchy = 'payment_date'
    readonly_fields = ('recorded_at',) # Usually don't want this editable

    def member_username(self, obj):
        return obj.member.user.username
    member_username.short_description = 'Member'

    def recorded_by_username(self, obj):
        return obj.recorded_by.username if obj.recorded_by else 'N/A'
    recorded_by_username.short_description = 'Recorded By'

    # Auto-set recorded_by on save in admin
    def save_model(self, request, obj, form, change):
        if not obj.pk: # Only set on creation
             obj.recorded_by = request.user
        super().save_model(request, obj, form, change)
