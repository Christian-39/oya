"""
Forms for OYA projects — EXTENDED with fundraising fields.
Replace your existing projects/forms.py with this file.
"""
from django import forms
from decimal import Decimal
from .models import Project


class ProjectForm(forms.ModelForm):
    """Form for creating and updating projects."""

    class Meta:
        model = Project
        fields = [
            "title", "budget", "description", "status", "progress_percentage",
            "enable_fundraising", "target_amount", "fundraising_start_date",
            "fundraising_end_date", "fundraising_status", "include_in_group_reports"
        ]
        widgets = {
            "title": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Project title"
            }),
            "budget": forms.NumberInput(attrs={
                "class": "form-control",
                "step": "0.01",
                "min": "0",
                "placeholder": "0.00"
            }),
            "description": forms.Textarea(attrs={
                "class": "form-control",
                "rows": 6,
                "placeholder": "Project description..."
            }),
            "status": forms.Select(attrs={"class": "form-select"}),
            "progress_percentage": forms.NumberInput(attrs={
                "class": "form-control",
                "min": "0",
                "max": "100",
                "placeholder": "0-100"
            }),
            "enable_fundraising": forms.CheckboxInput(attrs={
                "class": "form-check-input",
                "id": "id_enable_fundraising"
            }),
            "target_amount": forms.NumberInput(attrs={
                "class": "form-control",
                "step": "0.01",
                "min": "0",
                "placeholder": "0.00"
            }),
            "fundraising_start_date": forms.DateInput(attrs={
                "class": "form-control",
                "type": "date"
            }),
            "fundraising_end_date": forms.DateInput(attrs={
                "class": "form-control",
                "type": "date"
            }),
            "fundraising_status": forms.Select(attrs={"class": "form-select"}),
            "include_in_group_reports": forms.CheckboxInput(attrs={
                "class": "form-check-input",
                "id": "id_include_in_group_reports"
            }),
        }

    def clean_progress_percentage(self):
        progress = self.cleaned_data.get("progress_percentage")
        if progress is not None and (progress < 0 or progress > 100):
            raise forms.ValidationError("Progress must be between 0 and 100.")
        return progress

    def clean_budget(self):
        budget = self.cleaned_data.get("budget")
        if budget and budget < 0:
            raise forms.ValidationError("Budget cannot be negative.")
        return budget

    def clean_target_amount(self):
        target = self.cleaned_data.get("target_amount")
        if target and target < 0:
            raise forms.ValidationError("Target amount cannot be negative.")
        return target

    def clean(self):
        cleaned = super().clean()
        enable = cleaned.get("enable_fundraising")
        start = cleaned.get("fundraising_start_date")
        end = cleaned.get("fundraising_end_date")

        if enable:
            if not cleaned.get("target_amount"):
                self.add_error("target_amount", "Target amount is required when fundraising is enabled.")
            if start and end and start > end:
                self.add_error("fundraising_end_date", "End date cannot be before start date.")
        else:
            cleaned["target_amount"] = Decimal("0")
            cleaned["fundraising_start_date"] = None
            cleaned["fundraising_end_date"] = None
            cleaned["fundraising_status"] = "UPCOMING"

        return cleaned