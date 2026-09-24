"""
Admin configuration for elections app.
"""
from django.contrib import admin
from .models import Election, Candidate, HandoverLedger


@admin.register(Election)
class ElectionAdmin(admin.ModelAdmin):
    list_display = ["title", "start_date", "end_date", "status", "created_at"]
    list_filter = ["status", "start_date"]
    search_fields = ["title", "description"]
    ordering = ["-created_at"]


@admin.register(Candidate)
class CandidateAdmin(admin.ModelAdmin):
    list_display = ["member", "election", "post", "votes", "created_at"]
    list_filter = ["election", "post"]
    search_fields = ["member__full_name", "post"]
    list_select_related = ["member", "election"]


@admin.register(HandoverLedger)
class HandoverLedgerAdmin(admin.ModelAdmin):
    list_display = [
        "executive", "election", "tenure_start", "tenure_end",
        "cash_remaining", "net_balance", "net_financial_position", "created_at"
    ]
    list_filter = ["election", "tenure_start"]
    search_fields = ["executive__member__full_name", "election__title", "notes"]
    list_select_related = ["executive__member", "election"]
    readonly_fields = [
        "total_income", "total_dues", "total_donations", "taskforce_revenue",
        "total_expenses", "taskforce_total", "taskforce_active", "taskforce_inactive",
        "motorcycle_total", "motorcycle_excellent", "motorcycle_needs_service",
        "motorcycle_grounded", "motorcycle_acquired", "cases_total", "cases_open",
        "cases_in_progress", "cases_resolved", "projects_created", "projects_completed",
        "projects_at_hand", "projects_future", "pledges_made", "pledge_total_value",
        "created_at", "updated_at"
    ]
    fieldsets = (
        ("Basic Info", {
            "fields": ("election", "executive", "tenure_start", "tenure_end", "notes"),
            "description": (
                "tenure_start/tenure_end auto-populate from the selected executive's "
                "own record on save if left blank; every figure below is then "
                "recalculated automatically for that window — nothing here needs "
                "manual entry except Physical Cash at Hand below."
            )
        }),
        ("Physical Cash", {
            "fields": ("cash_remaining", "assets_description"),
            "description": "cash_remaining (\"Physical Cash at Hand\") is the only manually-entered figure on this ledger. It's administrator-only in the app UI; here in Django admin it follows normal staff permissions."
        }),
        ("Legacy Balances (deprecated)", {
            "fields": ("bank_balance", "cash_balance"),
            "classes": ("collapse",),
            "description": "Superseded by Physical Cash at Hand. Retained only for historical records created before this reform."
        }),
        ("Auto-Calculated Finance", {
            "fields": (
                "total_income", "total_dues", "total_donations",
                "taskforce_revenue", "total_expenses"
            ),
            "description": "These fields are auto-calculated from the tenure date range."
        }),
        ("Auto-Calculated Operations", {
            "fields": (
                ("taskforce_total", "taskforce_active", "taskforce_inactive"),
                ("motorcycle_total", "motorcycle_excellent", "motorcycle_needs_service", "motorcycle_grounded", "motorcycle_acquired"),
                ("cases_total", "cases_open", "cases_in_progress", "cases_resolved"),
            )
        }),
        ("Auto-Calculated Projects & Pledges", {
            "fields": (
                ("projects_created", "projects_completed", "projects_at_hand", "projects_future"),
                ("pledges_made", "pledge_total_value"),
            )
        }),
    )
