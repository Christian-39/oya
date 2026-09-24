"""
Forms for OYA Project Donations.
"""
from django import forms
from django.core.exceptions import ValidationError
from decimal import Decimal
from .models import OutsideDonor, Donation, Pledge, PledgePayment
from members.models import Member
from core.widgets import AutocompleteSelectWidget
from core.utils import exclude_admin_members


class OutsideDonorForm(forms.ModelForm):
    """Form for creating and updating outside donors."""

    class Meta:
        model = OutsideDonor
        fields = [
            "full_name", "profile_picture", "phone_number", "address",
            "gender", "occupation", "notes", "invited_by"
        ]
        widgets = {
            "full_name": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Full Name"
            }),
            "profile_picture": forms.FileInput(attrs={
                "class": "form-control"
            }),
            "phone_number": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Phone Number"
            }),
            "address": forms.Textarea(attrs={
                "class": "form-control",
                "rows": 2,
                "placeholder": "Address"
            }),
            "gender": forms.Select(attrs={
                "class": "form-select"
            }),
            "occupation": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Occupation"
            }),
            "notes": forms.Textarea(attrs={
                "class": "form-control",
                "rows": 3,
                "placeholder": "Additional notes..."
            }),
            "invited_by": AutocompleteSelectWidget(
                search_url_name="members:member_autocomplete_search",
                placeholder="Search member who invited this donor…",
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["invited_by"].queryset = exclude_admin_members(Member.objects.filter(
            status="ACTIVE"
        )).order_by("full_name")
        self.fields["invited_by"].widget.display_queryset = self.fields["invited_by"].queryset
        self.fields["invited_by"].required = True


class DonationForm(forms.ModelForm):
    """Form for creating and updating donations."""

    class Meta:
        model = Donation
        fields = [
            "project", "donor_type", "member", "outside_donor", "invited_by",
            "donation_type",
            "amount", "payment_method", "reference_number", "receipt", "narration",
            "material_name", "quantity", "labour_type", "number_of_days",
            "estimated_value", "remarks", "update_treasury",
            "donation_date", "status"
        ]
        widgets = {
            "project": forms.Select(attrs={"class": "form-select"}),
            "donor_type": forms.Select(attrs={
                "class": "form-select",
                "id": "id_donor_type"
            }),
            "member": AutocompleteSelectWidget(
                search_url_name="members:member_autocomplete_search",
                placeholder="Search member by name, no. or phone…",
                attrs={"id": "id_member"},
            ),
            "outside_donor": forms.Select(attrs={
                "class": "form-select",
                "id": "id_outside_donor"
            }),
            "invited_by": AutocompleteSelectWidget(
                search_url_name="members:member_autocomplete_search",
                placeholder="Search inviting member (optional)…",
            ),
            "donation_type": forms.Select(attrs={
                "class": "form-select",
                "id": "id_donation_type"
            }),
            "amount": forms.NumberInput(attrs={
                "class": "form-control",
                "step": "0.01",
                "min": "0.01",
                "placeholder": "0.00"
            }),
            "payment_method": forms.Select(attrs={"class": "form-select"}),
            "reference_number": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Reference / Receipt Number"
            }),
            "receipt": forms.FileInput(attrs={"class": "form-control"}),
            "narration": forms.Textarea(attrs={
                "class": "form-control",
                "rows": 2,
                "placeholder": "Narration or notes..."
            }),
            "material_name": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "e.g. Bags of Rice, Cement, Chairs"
            }),
            "quantity": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "e.g. 50 bags, 200kg, 20 units"
            }),
            "labour_type": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "e.g. Carpentry, Painting, Site Supervision"
            }),
            "number_of_days": forms.NumberInput(attrs={
                "class": "form-control",
                "min": "1",
                "placeholder": "Number of days"
            }),
            "estimated_value": forms.NumberInput(attrs={
                "class": "form-control",
                "step": "0.01",
                "min": "0",
                "placeholder": "Optional"
            }),
            "remarks": forms.Textarea(attrs={
                "class": "form-control",
                "rows": 2,
                "placeholder": "Remarks..."
            }),
            "update_treasury": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "donation_date": forms.DateInput(attrs={
                "class": "form-control",
                "type": "date"
            }),
            "status": forms.Select(attrs={"class": "form-select"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["member"].queryset = exclude_admin_members(Member.objects.filter(
            status="ACTIVE"
        )).order_by("full_name")
        self.fields["member"].widget.display_queryset = self.fields["member"].queryset
        self.fields["member"].required = False

        self.fields["outside_donor"].queryset = OutsideDonor.objects.select_related(
            "invited_by"
        ).order_by("full_name")
        self.fields["outside_donor"].empty_label = "-- Select Outside Donor --"
        self.fields["outside_donor"].required = False

        self.fields["invited_by"].queryset = exclude_admin_members(Member.objects.filter(
            status="ACTIVE"
        )).order_by("full_name")
        self.fields["invited_by"].widget.display_queryset = self.fields["invited_by"].queryset
        self.fields["invited_by"].required = False

        # Only show projects with fundraising enabled, but keep current project on edit
        from django.db.models import Q
        from projects.models import Project
        qs = Project.objects.filter(enable_fundraising=True)
        if self.instance and self.instance.pk and self.instance.project_id:
            qs = Project.objects.filter(
                Q(enable_fundraising=True) | Q(pk=self.instance.project_id)
            )
        self.fields["project"].queryset = qs.order_by("-created_at")
        self.fields["project"].empty_label = "-- Select Fundraising Project --"

    def clean(self):
        cleaned = super().clean()
        donor_type = cleaned.get("donor_type")
        member = cleaned.get("member")
        outside_donor = cleaned.get("outside_donor")

        if donor_type == "MEMBER":
            if not member:
                self.add_error("member", "Please select a member.")
            if outside_donor:
                self.add_error("outside_donor", "Clear outside donor for member donations.")
        elif donor_type == "OUTSIDE":
            if not outside_donor:
                self.add_error("outside_donor", "Please select an outside donor.")
            if member:
                self.add_error("member", "Clear member for outside donations.")

        donation_type = cleaned.get("donation_type")
        if donation_type == "MONEY":
            if not cleaned.get("amount"):
                self.add_error("amount", "Amount is required for Money donations.")
        elif donation_type == "MATERIAL":
            if not cleaned.get("material_name"):
                self.add_error("material_name", "Material name is required.")
            if not cleaned.get("quantity"):
                self.add_error("quantity", "Quantity is required.")
            if cleaned.get("update_treasury") and not cleaned.get("estimated_value"):
                self.add_error("estimated_value", "Estimated value is required to update treasury.")
        elif donation_type == "LABOUR":
            if not cleaned.get("labour_type"):
                self.add_error("labour_type", "Labour type is required.")
            if not cleaned.get("number_of_days"):
                self.add_error("number_of_days", "Number of days is required.")

        return cleaned

    def clean_amount(self):
        amount = self.cleaned_data.get("amount")
        if amount and amount <= 0:
            raise ValidationError("Amount must be greater than zero.")
        return amount

class PledgeForm(forms.ModelForm):
    """Form for recording a pledge directly from the Pledges module
    (Feature 6). Supports every donor and contribution type, mirroring
    DonationForm — a pledge made this way behaves exactly like a Donation
    saved with status="Pledge" except there's no Project Donation record
    driving it (it's fulfilled by editing this pledge's status directly)."""

    class Meta:
        model = Pledge
        fields = [
            "project", "donor_type", "member", "outside_donor",
            "donation_type", "pledged_amount",
            "material_name", "quantity", "labour_type", "number_of_days",
            "estimated_value",
            "due_date", "notes", "status",
        ]
        widgets = {
            "project": forms.Select(attrs={"class": "form-select"}),
            "donor_type": forms.Select(attrs={
                "class": "form-select", "id": "id_donor_type"
            }),
            "member": AutocompleteSelectWidget(
                search_url_name="members:member_autocomplete_search",
                placeholder="Search member by name, no. or phone…",
                attrs={"id": "id_member"},
            ),
            "outside_donor": forms.Select(attrs={
                "class": "form-select", "id": "id_outside_donor"
            }),
            "donation_type": forms.Select(attrs={
                "class": "form-select", "id": "id_donation_type"
            }),
            "pledged_amount": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "step": "0.01",
                    "min": "0.01",
                    "placeholder": "0.00",
                }
            ),
            "material_name": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "e.g. Bags of Cement, Roofing Sheets"
            }),
            "quantity": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "e.g. 50 bags, 20 sheets"
            }),
            "labour_type": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "e.g. Roofing, Carpentry, Electrical Wiring"
            }),
            "number_of_days": forms.NumberInput(attrs={
                "class": "form-control",
                "min": "1",
                "placeholder": "Number of days"
            }),
            "estimated_value": forms.NumberInput(attrs={
                "class": "form-control",
                "step": "0.01",
                "min": "0",
                "placeholder": "Optional"
            }),
            "due_date": forms.DateInput(
                attrs={"class": "form-control", "type": "date"}
            ),
            "notes": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 3,
                    "placeholder": "Notes...",
                }
            ),
            "status": forms.Select(attrs={"class": "form-select"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["member"].queryset = exclude_admin_members(Member.objects.filter(
            status="ACTIVE"
        )).order_by("full_name")
        self.fields["member"].widget.display_queryset = self.fields[
            "member"
        ].queryset
        self.fields["member"].required = False

        self.fields["outside_donor"].queryset = OutsideDonor.objects.select_related(
            "invited_by"
        ).order_by("full_name")
        self.fields["outside_donor"].empty_label = "-- Select Outside Donor --"
        self.fields["outside_donor"].required = False

        from projects.models import Project
        from django.db.models import Q

        qs = Project.objects.filter(enable_fundraising=True)
        if self.instance and self.instance.pk and self.instance.project_id:
            qs = Project.objects.filter(
                Q(enable_fundraising=True) | Q(pk=self.instance.project_id)
            )
        self.fields["project"].queryset = qs.order_by("-created_at")
        self.fields["project"].empty_label = "-- Select Fundraising Project --"

        # Status handling — a brand-new pledge always starts PENDING; once
        # it exists it can only be edited toward Cancelled or Completed
        # (Completed drives Money pledges too if you want to force-close
        # one without going through PledgePayments; Partially Paid stays
        # system-managed via recalculate_status for Money pledges).
        if not (self.instance and self.instance.pk):
            self.fields["status"].widget = forms.HiddenInput()
            self.fields["status"].required = False
            self.initial["status"] = "PENDING"
        else:
            self.fields["status"].choices = [
                c
                for c in Pledge.STATUS_CHOICES
                if c[0] in ("CANCELLED", "COMPLETED", self.instance.status)
            ]

    def clean(self):
        cleaned = super().clean()
        donor_type = cleaned.get("donor_type")
        member = cleaned.get("member")
        outside_donor = cleaned.get("outside_donor")

        if donor_type == "MEMBER":
            if not member:
                self.add_error("member", "Please select a member.")
            if outside_donor:
                self.add_error("outside_donor", "Clear outside donor for member pledges.")
        elif donor_type == "OUTSIDE":
            if not outside_donor:
                self.add_error("outside_donor", "Please select an outside donor.")
            if member:
                self.add_error("member", "Clear member for outside pledges.")

        donation_type = cleaned.get("donation_type")
        if donation_type == "MONEY":
            if not cleaned.get("pledged_amount"):
                self.add_error("pledged_amount", "Pledged amount is required for Money pledges.")
        elif donation_type == "MATERIAL":
            if not cleaned.get("material_name"):
                self.add_error("material_name", "Material name is required.")
            if not cleaned.get("quantity"):
                self.add_error("quantity", "Quantity is required.")
        elif donation_type == "LABOUR":
            if not cleaned.get("labour_type"):
                self.add_error("labour_type", "Labour type is required.")
            if not cleaned.get("number_of_days"):
                self.add_error("number_of_days", "Number of days is required.")

        return cleaned

    def clean_pledged_amount(self):
        amount = self.cleaned_data.get("pledged_amount")
        if amount and amount <= 0:
            raise forms.ValidationError(
                "Pledged amount must be greater than zero."
            )
        return amount



class PledgePaymentForm(forms.ModelForm):
    """Form for recording a payment against a pledge (Feature 7)."""

    class Meta:
        model = PledgePayment
        fields = ["amount", "payment_date", "payment_method", "reference_number", "notes"]
        widgets = {
            "amount": forms.NumberInput(attrs={
                "class": "form-control",
                "step": "0.01",
                "min": "0.01",
                "placeholder": "0.00"
            }),
            "payment_date": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
            "payment_method": forms.Select(attrs={"class": "form-select"}),
            "reference_number": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Reference Number"
            }),
            "notes": forms.Textarea(attrs={"class": "form-control", "rows": 2, "placeholder": "Notes..."}),
        }

    def __init__(self, *args, **kwargs):
        self.pledge = kwargs.pop("pledge", None)
        super().__init__(*args, **kwargs)

    def clean_amount(self):
        amount = self.cleaned_data.get("amount")
        if amount and amount <= 0:
            raise forms.ValidationError("Payment amount must be greater than zero.")
        if self.pledge and amount:
            # Exclude this instance's own current amount when editing, so
            # re-saving the same payment doesn't trip a false overpayment.
            already_paid = self.pledge.total_paid
            if self.instance and self.instance.pk:
                already_paid -= self.instance.amount
            outstanding = self.pledge.pledged_amount - already_paid
            if amount > outstanding:
                raise forms.ValidationError(
                    f"Payment exceeds the outstanding balance of ₦{outstanding:,.2f}."
                )
        return amount
