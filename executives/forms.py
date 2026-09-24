"""
Forms for OYA executives.
"""
from django import forms
from django.utils import timezone
from members.models import Member
from core.utils import exclude_removed_members
from .models import Executive


class ExecutiveForm(forms.ModelForm):
    """Form for creating and updating executives."""

    class Meta:
        model = Executive
        fields = ["member", "post", "start_date", "end_date", "is_current"]
        widgets = {
            "member": forms.Select(attrs={"class": "form-select"}),
            "post": forms.Select(attrs={"class": "form-select"}),
            "start_date": forms.DateInput(attrs={
                "class": "form-control",
                "type": "date"
            }),
            "end_date": forms.DateInput(attrs={
                "class": "form-control",
                "type": "date"
            }),
            "is_current": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Removed members must never be selectable/assignable as executives,
        # even if a request bypasses the view-level "available_members" list.
        from django.db.models import Q
        qs = exclude_removed_members(Member.objects.all())
        # If this is an edit and the currently-assigned member was removed
        # after being assigned, keep that value valid so the existing
        # record can still be edited/saved (mirrors the view's
        # available_members union for the same case).
        if self.instance and self.instance.pk and self.instance.member_id:
            qs = Member.objects.filter(Q(pk=self.instance.member_id) | Q(pk__in=qs.values_list("pk", flat=True)))
        self.fields["member"].queryset = qs.order_by("full_name")

    def clean(self):
        cleaned_data = super().clean()
        end_date = cleaned_data.get("end_date")
        is_current = cleaned_data.get("is_current")

        if end_date and is_current:
            raise forms.ValidationError(
                "An executive with an end date cannot be marked as current."
            )

        if not end_date and not is_current:
            raise forms.ValidationError(
                "Either set an end date or mark as current."
            )

        return cleaned_data