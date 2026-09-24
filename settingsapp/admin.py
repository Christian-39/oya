"""
Admin configuration for settingsapp.
"""
from django.contrib import admin
from django.utils.html import format_html
from .models import SystemSettings, DonationGroup, DonationGroupMembership


class DonationGroupMembershipInline(admin.TabularInline):
    model = DonationGroupMembership
    extra = 0
    autocomplete_fields = []
    fields = ["member", "date_added", "added_by"]
    readonly_fields = ["date_added"]


@admin.register(DonationGroup)
class DonationGroupAdmin(admin.ModelAdmin):
    list_display = ["name", "minimum_amount", "maximum_amount", "is_active", "member_count", "created_by", "created_at"]
    list_filter = ["is_active"]
    search_fields = ["name", "description"]
    readonly_fields = ["created_at", "updated_at", "created_by"]
    inlines = [DonationGroupMembershipInline]

    def member_count(self, obj):
        return obj.member_count
    member_count.short_description = "Members"

    def save_model(self, request, obj, form, change):
        if not change:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(DonationGroupMembership)
class DonationGroupMembershipAdmin(admin.ModelAdmin):
    list_display = ["member", "group", "date_added", "added_by"]
    list_filter = ["group"]
    search_fields = ["member__full_name", "member__serial_number", "group__name"]
    readonly_fields = ["date_added"]


@admin.register(SystemSettings)
class SystemSettingsAdmin(admin.ModelAdmin):
    list_display = ["association_name", "yearly_dues", "minimum_age", "past_member_age", "updated_at"]
    readonly_fields = ["updated_at", "logo_preview", "favicon_preview"]

    fieldsets = (
        ("Organization Info", {
            "fields": ("association_name", "motto", "logo", "logo_preview", "favicon", "favicon_preview")
        }),
        ("Financial Settings", {
            "fields": ("yearly_dues", "minimum_age", "past_member_age")
        }),
        ("Appearance", {
            "fields": ("primary_color", "accent_color", "theme_mode")
        }),
    )

    def logo_preview(self, obj):
        if obj.logo and obj.logo.name:
            return format_html(
                '<img src="{}" style="max-height:80px;max-width:200px;border-radius:4px;" />',
                obj.logo.url
            )
        return "No logo uploaded"
    logo_preview.short_description = "Logo Preview"

    def favicon_preview(self, obj):
        if obj.favicon and obj.favicon.name:
            return format_html(
                '<img src="{}" style="max-height:32px;max-width:32px;border-radius:2px;" />',
                obj.favicon.url
            )
        return "No favicon uploaded"
    favicon_preview.short_description = "Favicon Preview"

    def has_add_permission(self, request):
        """Prevent adding new settings instances."""
        return not SystemSettings.objects.exists()

    def has_delete_permission(self, request, obj=None):
        """Prevent deleting settings."""
        return False
