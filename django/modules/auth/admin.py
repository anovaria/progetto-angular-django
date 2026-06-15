# modules/auth/admin.py
from django.contrib import admin
from .models import UserAppPermission


@admin.register(UserAppPermission)
class UserAppPermissionAdmin(admin.ModelAdmin):
    list_display = ['username', 'app_name', 'created_at']
    list_filter = ['app_name']
    search_fields = ['username', 'app_name']
    ordering = ['username', 'app_name']
    
    # Per aggiungere velocemente più permessi
    list_editable = ['app_name']