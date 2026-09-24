"""Admin configuration for finance app."""
from django.contrib import admin
from .models import Income, Expense, DuesPayment, DuesPaymentTransaction


@admin.register(Income)
class IncomeAdmin(admin.ModelAdmin):
    list_display = ["reason", "amount", "income_type", "get_payer", "case", "created_by", "created_at"]
    list_filter = ["created_at", "income_type"]
    search_fields = ["reason", "paid_by", "member__full_name", "member__serial_number", "case__case_number", "case__title"]
    ordering = ["-created_at"]
    autocomplete_fields = ["member", "created_by", "case"]
    
    def get_payer(self, obj):
        return obj.get_payer_display()
    get_payer.short_description = "Paid By"


@admin.register(DuesPaymentTransaction)
class DuesPaymentTransactionAdmin(admin.ModelAdmin):
    list_display = [
        "member", "total_amount", "payment_method", "payment_date",
        "receipt_reference", "recorded_by", "created_at",
    ]
    list_filter = ["payment_method", "payment_date", "created_at"]
    search_fields = ["member__full_name", "receipt_reference", "notes"]
    ordering = ["-payment_date"]
    autocomplete_fields = ["member", "recorded_by"]


@admin.register(DuesPayment)
class DuesPaymentAdmin(admin.ModelAdmin):
    list_display = [
        "member", "year", "amount_paid", "status", "recorded_by", "created_at",
    ]
    list_filter = ["year", "created_at"]
    search_fields = ["member__full_name", "notes"]
    ordering = ["-year", "member__full_name"]
    autocomplete_fields = ["member", "recorded_by"]


@admin.register(Expense)
class ExpenseAdmin(admin.ModelAdmin):
    list_display = ["category", "amount", "description", "created_by", "created_at"]
    list_filter = ["category", "created_at"]
    search_fields = ["description", "category"]
    ordering = ["-created_at"]