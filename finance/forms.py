"""Forms for OYA finance."""
from django import forms
from django.core.exceptions import ValidationError
from django.utils import timezone
from decimal import Decimal
from .models import Income, Expense, DuesPayment, DuesPaymentTransaction
from accounts.models import User  # Ensure this import matches your user model path
from core.widgets import AutocompleteSelectWidget
from core.utils import exclude_removed_users, exclude_admin_users


class IncomeForm(forms.ModelForm):
    """Form for creating and updating income records (Donations, Events, Other, Case Fines)."""

    class Meta:
        model = Income
        fields = ["income_type", "case", "amount", "reason", "member", "paid_by"]
        widgets = {
            "income_type": forms.Select(attrs={"class": "form-select"}),
            "case": forms.Select(attrs={"class": "form-select", "id": "id_case"}),
            "amount": forms.NumberInput(attrs={
                "class": "form-control",
                "step": "0.01",
                "min": "0.01",
                "placeholder": "0.00"
            }),
            "reason": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "e.g., Donation for project, Event ticket sales"
            }),
            "member": AutocompleteSelectWidget(
                search_url_name="accounts:user_search_ajax",
                placeholder="Search member by name, no. or phone (optional)…",
                attrs={"id": "id_member"},
            ),
            "paid_by": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Name of payer / contributor (if not a member)"
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["income_type"].initial = "DONATION"
        choices = [c for c in Income.INCOME_TYPE_CHOICES if c[0] != "DUES"]
        self.fields["income_type"].choices = choices

        # Member dropdown — Admins don't donate; Removed members must never
        # be selectable either.
        member_qs = User.objects.filter(serial_number__isnull=False).exclude(serial_number="")
        member_qs = exclude_admin_users(member_qs)
        self.fields["member"].queryset = exclude_removed_users(member_qs).order_by("full_name")
        self.fields["member"].widget.display_queryset = self.fields["member"].queryset
        self.fields["member"].required = False
        self.fields["paid_by"].required = False

        # NEW: Case dropdown — only resolved cases that carry a fine
        from operations.models import CaseFile
        self.fields["case"].queryset = CaseFile.objects.filter(
            status="RESOLVED",
            fine_amount__gt=0
        ).order_by("-created_at")
        self.fields["case"].empty_label = "--------- Select Resolved Case ---------"
        self.fields["case"].required = False

    def clean_amount(self):
        amount = self.cleaned_data.get("amount")
        income_type = self.cleaned_data.get("income_type")
        case = self.cleaned_data.get("case")
        # Auto-fill amount from case fine when case type is selected
        if income_type == "CASE_FINE" and case and not amount:
            return case.fine_amount
        if amount and amount <= 0:
            raise ValidationError("Amount must be greater than zero.")
        return amount

    def clean_reason(self):
        reason = self.cleaned_data.get("reason")
        income_type = self.cleaned_data.get("income_type")
        case = self.cleaned_data.get("case")
        if income_type == "CASE_FINE" and case and not reason:
            return f"Case Fine — {case.case_number}: {case.title}"
        return reason

    def clean_paid_by(self):
        paid_by = self.cleaned_data.get("paid_by")
        income_type = self.cleaned_data.get("income_type")
        case = self.cleaned_data.get("case")
        if income_type == "CASE_FINE" and case and not paid_by:
            return case.respondent.full_name
        return paid_by

    def clean(self):
        cleaned = super().clean()
        income_type = cleaned.get("income_type")
        case = cleaned.get("case")
        member = cleaned.get("member")
        paid_by = cleaned.get("paid_by")

        if income_type == "CASE_FINE":
            if not case:
                raise ValidationError(
                    {"case": "Please select the case this fine was collected from."}
                )
            # Case fines auto-fill payer from respondent; member link is optional
        else:
            # Original validation for non-case income
            if member and not paid_by:
                cleaned["paid_by"] = member.get_full_name()
            if not member and not paid_by:
                raise ValidationError(
                    "Please either select a member from the dropdown or enter a payer name."
                )

        return cleaned


class DuesPaymentAllocationForm(forms.ModelForm):
    """
    Form for recording smart dues payment allocations.
    Administrator enters total amount; system auto-allocates across years.
    """
    class Meta:
        model = DuesPaymentTransaction
        fields = ["member", "total_amount", "payment_method", "receipt_reference", "payment_date", "notes"]
        widgets = {
            "member": AutocompleteSelectWidget(
                search_url_name="accounts:user_search_ajax",
                placeholder="Search member by name, no. or phone…",
            ),
            "total_amount": forms.NumberInput(attrs={
                "class": "form-control",
                "step": "0.01",
                "min": "0.01",
                "placeholder": "0.00",
            }),
            "payment_method": forms.Select(attrs={"class": "form-select"}),
            "receipt_reference": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "e.g., TRX-123456, Receipt #001",
            }),
            "payment_date": forms.DateInput(attrs={
                "class": "form-control",
                "type": "date",
            }),
            "notes": forms.Textarea(attrs={
                "class": "form-control",
                "rows": 2,
                "placeholder": "Payment method details, reference number, etc.",
            }),
        }

    def __init__(self, *args, **kwargs):
        self.recorded_by = kwargs.pop("recorded_by", None)
        super().__init__(*args, **kwargs)
        self.fields["payment_date"].initial = timezone.now().date()
        # Ensure only registered members appear in dues allocation form —
        # Admins don't pay dues; Removed members must never be selectable
        # for new dues payments either.
        member_qs = User.objects.filter(
            serial_number__isnull=False
        ).exclude(
            serial_number=""
        )
        member_qs = exclude_admin_users(member_qs)
        self.fields["member"].queryset = exclude_removed_users(member_qs).order_by("full_name")
        self.fields["member"].widget.display_queryset = self.fields["member"].queryset

    def clean_total_amount(self):
        amount = self.cleaned_data.get("total_amount")
        if not amount or amount <= 0:
            raise ValidationError("Payment amount must be greater than zero.")
        return amount

    def clean_payment_date(self):
        payment_date = self.cleaned_data.get("payment_date")
        if payment_date and payment_date > timezone.now().date():
            raise ValidationError("Payment date cannot be in the future.")
        return payment_date

    def allocate(self):
        """
        Execute the allocation logic. Must be called after form is_valid().
        Returns the allocation result dict from DuesPayment.allocate_payment().
        """
        if not self.is_valid():
            raise ValidationError("Form must be valid before allocation.")

        member = self.cleaned_data["member"]
        total_amount = self.cleaned_data["total_amount"]
        payment_method = self.cleaned_data.get("payment_method", "CASH")
        receipt_reference = self.cleaned_data.get("receipt_reference", "")
        payment_date = self.cleaned_data.get("payment_date", timezone.now().date())
        notes = self.cleaned_data.get("notes", "")

        return DuesPayment.allocate_payment(
            member=member,
            total_amount=total_amount,
            payment_method=payment_method,
            receipt_reference=receipt_reference,
            payment_date=payment_date,
            notes=notes,
            recorded_by=self.recorded_by,
        )


class ExpenseForm(forms.ModelForm):
    """Form for creating and updating expense records."""

    class Meta:
        model = Expense
        fields = ["amount", "category", "description", "receipt_file"]
        widgets = {
            "amount": forms.NumberInput(attrs={
                "class": "form-control",
                "step": "0.01",
                "min": "0.01",
                "placeholder": "0.00"
            }),
            "category": forms.Select(attrs={"class": "form-select"}),
            "description": forms.Textarea(attrs={
                "class": "form-control",
                "rows": 4,
                "placeholder": "Describe the expense..."
            }),
            "receipt_file": forms.FileInput(attrs={
                "class": "form-control",
                "accept": ".pdf,.jpg,.jpeg,.png"
            }),
        }

    def clean_amount(self):
        amount = self.cleaned_data.get("amount")
        if amount and amount <= 0:
            raise ValidationError("Amount must be greater than zero.")
        return amount

    def clean_receipt_file(self):
        receipt = self.cleaned_data.get("receipt_file")
        if receipt:
            if receipt.size > 10 * 1024 * 1024:
                raise ValidationError("Receipt file must be under 10MB.")
        return receipt