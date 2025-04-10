from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.translation import gettext_lazy as _

from .models import User, OTP

@admin.register(User)
class CustomUserAdmin(UserAdmin):
    """
    Custom User Admin to handle our custom User model.
    """
    list_display = ('email', 'full_name', 'is_staff', 'is_passenger')
    list_filter = ('is_staff', 'is_superuser', 'is_active', 'is_passenger')
    search_fields = ('email', 'full_name')
    ordering = ('email',)
    
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        (_('Personal info'), {'fields': ('full_name', 'profile_picture_url')}),
        (_('Permissions'), {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'is_passenger', 'groups', 'user_permissions'),
        }),
        (_('Important dates'), {'fields': ('last_login', 'date_joined')}),
    )
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'full_name', 'password1', 'password2'),
        }),
    )

@admin.register(OTP)
class OTPAdmin(admin.ModelAdmin):
    """
    Admin interface for OTP model.
    """
    list_display = ('email', 'action', 'code', 'created_at', 'expires_at', 'is_used')
    list_filter = ('action', 'is_used', 'created_at')
    search_fields = ('email', 'code')
    readonly_fields = ('created_at', 'expires_at')
    ordering = ('-created_at',)
