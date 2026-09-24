"""
Forms for OYA operations.
"""
from django import forms
from members.models import Member
from core.utils import exclude_removed_members, exclude_admin_members
from .models import TaskForceMember, Motorcycle, CaseFile


class TaskForceMemberForm(forms.ModelForm):
    """Form for creating and updating task force members."""

    class Meta:
        model = TaskForceMember
        fields = ["member", "assigned_date", "notes", "is_active"]
        widgets = {
            "member": forms.Select(attrs={"class": "form-select"}),
            "assigned_date": forms.DateInput(attrs={
                "class": "form-control",
                "type": "date"
            }),
            "notes": forms.Textarea(attrs={
                "class": "form-control",
                "rows": 3,
                "placeholder": "Additional notes..."
            }),
            "is_active": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Removed members, Admins, and members who are currently serving as
        # an executive must never be newly selectable for task force
        # assignment, but keep an already-assigned member selectable when
        # editing an existing assignment, even if they were removed or
        # became an executive after being assigned (so the record can
        # still be edited/saved).
        from django.db.models import Q
        from executives.models import Executive
        current_executive_ids = Executive.objects.filter(
            is_current=True
        ).values_list("member_id", flat=True)
        qs = exclude_admin_members(exclude_removed_members(Member.objects.all())).exclude(
            id__in=current_executive_ids
        )
        if self.instance and self.instance.pk and self.instance.member_id:
            qs = Member.objects.filter(Q(pk=self.instance.member_id) | Q(pk__in=qs.values_list("pk", flat=True)))
        self.fields["member"].queryset = qs.order_by("full_name")


class MotorcycleForm(forms.ModelForm):
    """Form for creating and updating motorcycle records."""

    class Meta:
        model = Motorcycle
        fields = ["asset_tag", "brand", "model", "year", "condition", "assigned_to"]
        widgets = {
            "asset_tag": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "e.g., OYA-MC-001"
            }),
            "brand": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "e.g., Honda"
            }),
            "model": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "e.g., CG125"
            }),
            "year": forms.NumberInput(attrs={
                "class": "form-control",
                "min": "1900",
                "max": "2099"
            }),
            "condition": forms.Select(attrs={"class": "form-select"}),
            "assigned_to": forms.Select(attrs={"class": "form-select"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Removed members and Admins must never be newly assignable to an
        # asset, but keep an already-assigned member selectable when
        # editing an existing record, even if they were removed afterward.
        from django.db.models import Q
        qs = exclude_admin_members(exclude_removed_members(Member.objects.all()))
        if self.instance and self.instance.pk and self.instance.assigned_to_id:
            qs = Member.objects.filter(Q(pk=self.instance.assigned_to_id) | Q(pk__in=qs.values_list("pk", flat=True)))
        self.fields["assigned_to"].queryset = qs.order_by("full_name")
        self.fields["assigned_to"].required = False


class CaseFileForm(forms.ModelForm):
    """Form for creating and updating case files."""

    class Meta:
        model = CaseFile
        fields = [
            "title", "description",
            "fine_amount", "status", "respondent", "reported_to"
        ]
        widgets = {
            "title": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Case title"
            }),
            "description": forms.Textarea(attrs={
                "class": "form-control",
                "rows": 6,
                "placeholder": "Detailed description of the case..."
            }),
            "fine_amount": forms.NumberInput(attrs={
                "class": "form-control",
                "step": "0.01",
                "min": "0",
                "placeholder": "0.00"
            }),
            "status": forms.Select(attrs={"class": "form-select"}),
            "respondent": forms.Select(attrs={"class": "form-select"}),
            "reported_to": forms.Select(attrs={"class": "form-select"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Removed members must never be newly selectable as a case
        # respondent, but keep an already-selected respondent valid when
        # editing an existing case, even if they were removed afterward.
        from django.db.models import Q
        respondent_qs = exclude_removed_members(Member.objects.all())
        if self.instance and self.instance.pk and self.instance.respondent_id:
            respondent_qs = Member.objects.filter(
                Q(pk=self.instance.respondent_id) | Q(pk__in=respondent_qs.values_list("pk", flat=True))
            )
        self.fields["respondent"].queryset = respondent_qs.order_by("full_name")
        # Also guard against a task-force member whose linked Member was
        # marked Removed after being assigned (is_active alone wouldn't
        # catch that).
        self.fields["reported_to"].queryset = TaskForceMember.objects.filter(
            is_active=True
        ).exclude(
            member__status="REMOVED"
        ).select_related("member").order_by("member__full_name")
        self.fields["reported_to"].empty_label = "--------- Select Task Force Member ---------"
        self.fields["reported_to"].label = "Reported To (Task Force)"


class CaseResolutionForm(forms.ModelForm):
    """Form for resolving a case."""

    class Meta:
        model = CaseFile
        fields = ["status", "resolution_notes", "resolved_date", "resolved_by"]
        widgets = {
            "status": forms.Select(attrs={"class": "form-select"}),
            "resolution_notes": forms.Textarea(attrs={
                "class": "form-control",
                "rows": 4,
                "placeholder": "Resolution details..."
            }),
            "resolved_date": forms.DateInput(attrs={
                "class": "form-control",
                "type": "date"
            }),
            "resolved_by": forms.Select(attrs={"class": "form-select"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Only active task-force members can resolve; also exclude a member
        # who was marked Removed after being assigned to the task force.
        self.fields["resolved_by"].queryset = TaskForceMember.objects.filter(
            is_active=True
        ).exclude(
            member__status="REMOVED"
        ).select_related("member").order_by("member__full_name")
        self.fields["resolved_by"].empty_label = "--------- Select Task Force Member ---------"
        self.fields["resolved_by"].label = "Resolved By (Task Force)"