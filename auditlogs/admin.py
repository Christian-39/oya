"""
Admin configuration for auditlogs app.
"""
from django.contrib import admin
from .models import AuditLog


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = [
        "id", "user", "action", "object_type",
        "object_id", "ip_address", "created_at"
    ]
    list_filter = ["action", "object_type", "created_at"]
    search_fields = [
        "user__full_name", "user__serial_number",
        "description", "ip_address", "object_type"
    ]
    ordering = ["-created_at"]
    readonly_fields = [
        "user", "action", "object_type", "object_id",
        "description", "ip_address", "created_at"
    ]
    list_per_page = 50

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser