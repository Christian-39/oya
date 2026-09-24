"""
Admin configuration for members app.
"""
from django.contrib import admin
from .models import Clan, Member


@admin.register(Clan)
class ClanAdmin(admin.ModelAdmin):
    list_display = ["id", "name"]
    search_fields = ["name"]
    ordering = ["name"]


@admin.register(Member)
class MemberAdmin(admin.ModelAdmin):
    list_display = [
        "serial_number", "full_name", "age",
        "umu_nna_clan", "status", "state_or_abroad", "created_at"
    ]
    list_filter = ["status", "umu_nna_clan", "created_at"]
    search_fields = ["serial_number", "full_name", "phone", "state_or_abroad"]
    list_select_related = ["umu_nna_clan"]
    ordering = ["-created_at"]
 