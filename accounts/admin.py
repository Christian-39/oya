"""
Admin configuration for accounts app.
"""
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """Admin configuration for User model."""

    list_display = [
        "serial_number", "full_name", "role", "phone",
        "state", "is_active", "date_joined"
    ]
    list_filter = ["role", "is_active", "state", "date_joined"]
    search_fields = ["serial_number", "full_name", "phone", "state"]
    ordering = ["-date_joined"]

    fieldsets = [
        (None, {"fields": ["serial_number", "password"]}),
        ("Personal Info", {"fields": ["full_name", "phone", "state", "photo"]}),
        ("Role & Permissions", {"fields": ["role", "is_active", "is_staff", "is_superuser", "groups", "user_permissions"]}),
        ("Important Dates", {"fields": ["last_login", "date_joined"]}),
    ]

    add_fieldsets = [
        (
            None,
            {
                "classes": ["wide"],
                "fields": ["serial_number", "full_name", "phone", "state", "role", "password1", "password2"],
            },
        ),
    ]

    readonly_fields = ["last_login", "date_joined"]
