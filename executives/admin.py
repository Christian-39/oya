"""
Admin configuration for executives app.
"""
from django.contrib import admin
from .models import Executive


@admin.register(Executive)
class ExecutiveAdmin(admin.ModelAdmin):
    list_display = [
        "member", "post", "start_date", "end_date", "is_current", "elected_via", "created_at"
    ]
    list_filter = ["is_current", "post", "start_date", "elected_via"]
    search_fields = ["member__full_name", "member__serial_number", "post"]
    list_select_related = ["member", "elected_via"]
    ordering = ["-is_current", "-start_date"]
    date_hierarchy = "start_date"
