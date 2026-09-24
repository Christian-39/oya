"""
Admin configuration for operations app.
"""
from django.contrib import admin
from .models import TaskForceMember, Motorcycle, CaseFile


@admin.register(TaskForceMember)
class TaskForceMemberAdmin(admin.ModelAdmin):
    list_display = ["member", "assigned_date", "is_active", "created_at"]
    list_filter = ["is_active", "assigned_date"]
    search_fields = ["member__full_name"]
    list_select_related = ["member"]


@admin.register(Motorcycle)
class MotorcycleAdmin(admin.ModelAdmin):
    list_display = ["asset_tag", "brand", "model", "condition", "assigned_to"]
    list_filter = ["condition"]
    search_fields = ["asset_tag", "brand", "model"]
    list_select_related = ["assigned_to"]


@admin.register(CaseFile)
class CaseFileAdmin(admin.ModelAdmin):
    list_display = ["case_number", "title", "respondent", "status", "fine_amount", "reported_to", "resolved_by", "created_at"]
    list_filter = ["status", "created_at"]
    search_fields = ["case_number", "title", "respondent__full_name", "reported_to__member__full_name", "resolved_by__member__full_name"]
    list_select_related = ["respondent", "reported_to", "reported_to__member", "resolved_by", "resolved_by__member"]