"""
Admin configuration for OYA Project Donations.
"""
from django.contrib import admin
from .models import OutsideDonor, Donation, Pledge, PledgePayment


@admin.register(OutsideDonor)
class OutsideDonorAdmin(admin.ModelAdmin):
    list_display = [
        "full_name", "phone_number", "occupation",
        "invited_by", "created_at", "total_donations"
    ]
    list_filter = ["gender", "created_at"]
    search_fields = [
        "full_name", "phone_number", "occupation",
        "invited_by__full_name"
    ]
    raw_id_fields = ["invited_by"]
    readonly_fields = ["total_donations", "donation_count", "projects_supported"]


@admin.register(Donation)
class DonationAdmin(admin.ModelAdmin):
    list_display = [
        "project", "donor_type", "donation_type", "get_donor_name", "amount",
        "donation_date", "status", "recorded_by"
    ]
    list_filter = [
        "donor_type", "donation_type", "status", "payment_method", "donation_date"
    ]
    search_fields = [
        "project__title", "member__full_name", "outside_donor__full_name",
        "reference_number", "narration"
    ]
    raw_id_fields = [
        "project", "member", "outside_donor", "invited_by", "recorded_by", "pledge"
    ]
    date_hierarchy = "donation_date"

    def get_donor_name(self, obj):
        if obj.member:
            return obj.member.full_name
        elif obj.outside_donor:
            return obj.outside_donor.full_name
        return "Anonymous"
    get_donor_name.short_description = "Donor"

class PledgePaymentInline(admin.TabularInline):
    model = PledgePayment
    extra = 0
    fields = ["amount", "payment_date", "payment_method", "reference_number", "recorded_by"]
    raw_id_fields = ["recorded_by"]


@admin.register(Pledge)
class PledgeAdmin(admin.ModelAdmin):
    list_display = [
        "donor", "project", "donation_type", "display_value", "total_paid",
        "outstanding_balance", "status", "due_date"
    ]
    list_filter = ["status", "donation_type", "donor_type", "due_date"]
    search_fields = [
        "member__full_name", "member__serial_number",
        "outside_donor__full_name", "project__title"
    ]
    raw_id_fields = ["member", "outside_donor", "project", "created_by"]
    readonly_fields = ["total_paid", "outstanding_balance"]
    date_hierarchy = "due_date"
    inlines = [PledgePaymentInline]


@admin.register(PledgePayment)
class PledgePaymentAdmin(admin.ModelAdmin):
    list_display = ["pledge", "amount", "payment_date", "payment_method", "recorded_by"]
    list_filter = ["payment_method", "payment_date"]
    search_fields = ["pledge__member__full_name", "reference_number"]
    raw_id_fields = ["pledge", "recorded_by", "donation"]
    date_hierarchy = "payment_date"
