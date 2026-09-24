"""
Admin configuration for projects app.
"""
from django.contrib import admin
from .models import Project


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = [
        "title", "budget", "status", "progress_percentage",
        "enable_fundraising", "fundraising_status", "created_at"
    ]
    list_filter = ["status", "enable_fundraising", "fundraising_status", "created_at"]
    search_fields = ["title", "description"]
    ordering = ["-created_at"]