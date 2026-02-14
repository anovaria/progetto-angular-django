"""
Active Users - Admin
Registrazione nel pannello admin Django.
Da aggiungere in modules/active_users/admin.py
"""
from django.contrib import admin
from .models import UserActivity


@admin.register(UserActivity)
class UserActivityAdmin(admin.ModelAdmin):
    list_display = ('username', 'display_name', 'environment', 'last_activity', 'last_path', 'ip_address')
    list_filter = ('environment', 'last_activity')
    search_fields = ('username', 'display_name', 'ip_address')
    readonly_fields = ('username', 'display_name', 'environment', 'last_activity', 'last_path', 'ip_address', 'user_agent')
    ordering = ('-last_activity',)

    def has_add_permission(self, request):
        return False  # I record vengono creati solo dal middleware

    def has_change_permission(self, request, obj=None):
        return False
