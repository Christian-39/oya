"""
Forms for OYA elections.
"""
from django import forms
from django.core.exceptions import ValidationError
from .models import Election, Candidate, HandoverLedger
from executives.models import Executive
from members.models import Member
from core.utils import exclude_removed_members, exclude_admin_members


class ElectionForm(forms.ModelForm):
    """Form for creating and updating elections."""

    class Meta:
        model = Election
        fields = ["title", "start_date", "end_date", "status", "description"]
        widgets = {
            "title": forms.TextInput(attrs={"class": "form-control"}),
            "start_date": forms.DateTimeInput(attrs={
                "class": "form-control",
                "type": "datetime-local"
            }),
            "end_date": forms.DateTimeInput(attrs={
                "class": "form-control",
                "type": "datetime-local"
            }),
            "status": forms.Select(attrs={"class": "form-select"}),
            "description": forms.Textarea(attrs={
                "class": "form-control",
                "rows": 4
            }),
        }

    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get("start_date")
        end_date = cleaned_data.get("end_date")

        if start_date and end_date and end_date <= start_date:
            raise ValidationError("End date must be after start date.")

        return cleaned_data


class CandidateForm(forms.ModelForm):
    """Form for creating and updating candidates."""

    class Meta:
        model = Candidate
        fields = ["election", "member", "post", "photo", "manifesto"]
        widgets = {
            "election": forms.Select(attrs={"class": "form-select"}),
            "member": forms.Select(attrs={"class": "form-select"}),
            "post": forms.Select(attrs={"class": "form-select"}),
            "photo": forms.FileInput(attrs={"class": "form-control"}),
            "manifesto": forms.Textarea(attrs={
                "class": "form-control",
                "rows": 6,
                "placeholder": "Candidate manifesto..."
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Removed members, Admins, and members who are currently active on
        # the task force must never be newly nominable as election
        # candidates, but keep an already-nominated candidate's member
        # selectable when editing an existing record, even if they were
        # removed or joined the task force afterward.
        from django.db.models import Q
        from operations.models import TaskForceMember
        active_taskforce_ids = TaskForceMember.objects.filter(
            is_active=True
        ).values_list("member_id", flat=True)
        qs = exclude_admin_members(exclude_removed_members(Member.objects.all())).exclude(
            id__in=active_taskforce_ids
        )
        if self.instance and self.instance.pk and self.instance.member_id:
            qs = Member.objects.filter(Q(pk=self.instance.member_id) | Q(pk__in=qs.values_list("pk", flat=True)))
        self.fields["member"].queryset = qs.order_by("full_name")
        # Populate post choices dynamically from Executive.POST_CHOICES
        self.fields["post"].widget = forms.Select(
            attrs={"class": "form-select"},
            choices=Executive.POST_CHOICES
        )
        self.fields["post"].choices = [("", "Select position")] + list(Executive.POST_CHOICES)


class HandoverLedgerForm(forms.ModelForm):
    """Form for creating and updating handover ledgers.

    Reformed so the only manual, editable figure is Physical Cash at Hand
    (`cash_remaining`) — administrator-only: pass `user=` into the
    constructor and the field is removed entirely for non-admin users (so
    it can never be tampered with via POST), keeping the model default of
    ₦0.00 until an administrator sets it. Tenure dates are derived
    automatically from the selected executive's own record, and every
    financial/statistical figure is recalculated automatically from
    existing records for that tenure window — see
    HandoverLedger.recalculate_aggregates(), which reuses the same
    calculation engine as the Executive Handover Report
    (elections.administrations) so the two always agree.
    """

    class Meta:
        model = HandoverLedger
        fields = [
            "election", "executive", "cash_remaining",
            "assets_description", "notes"
        ]
        widgets = {
            "election": forms.Select(attrs={"class": "form-select"}),
            "executive": forms.Select(attrs={"class": "form-select"}),
            "cash_remaining": forms.NumberInput(attrs={
                "class": "form-control",
                "step": "0.01",
                "min": "0",
                "placeholder": "0.00"
            }),
            "assets_description": forms.Textarea(attrs={
                "class": "form-control",
                "rows": 4,
                "placeholder": "List all assets being handed over (motorcycles, equipment, documents, etc.)..."
            }),
            "notes": forms.Textarea(attrs={
                "class": "form-control",
                "rows": 3,
                "placeholder": "Additional notes about the handover..."
            }),
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        is_admin = bool(user and user.has_admin_access())
        if not is_admin:
            # Non-admins never see or can submit this field — the model
            # default (₦0.00) or the existing stored value is preserved.
            self.fields.pop("cash_remaining", None)

    def save(self, commit=True):
        instance = super().save(commit=False)
        # Tenure dates + every aggregate figure are derived automatically
        # from the selected executive and existing records — see
        # HandoverLedger.recalculate_aggregates().
        instance.recalculate_aggregates()
        if commit:
            instance.save()
        return instance