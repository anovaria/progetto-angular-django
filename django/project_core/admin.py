from django.contrib import admin
from .models import AppGroup

@admin.register(AppGroup)
class AppGroupAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'active')
    list_filter = ('active',)
    search_fields = ('name',)
