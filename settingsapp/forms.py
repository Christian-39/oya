"""
Forms for OYA system settings.
"""
from django import forms
from .models import SystemSettings, DonationGroup, DonationGroupMembership
from core.widgets import AutocompleteSelectWidget
from core.utils import exclude_admin_members
from members.models import Member


class SystemSettingsForm(forms.ModelForm):
    """Form for updating system settings."""

    class Meta:
        model = SystemSettings
        fields = [
            "association_name", "motto",
            "logo", "favicon",
            "yearly_dues", "minimum_age", "past_member_age",
            "primary_color", "accent_color", "theme_mode"
        ]
        widgets = {
            "association_name": forms.TextInput(attrs={"class": "form-control"}),
            "motto": forms.TextInput(attrs={"class": "form-control"}),
            "logo": forms.ClearableFileInput(attrs={
                "class": "form-control",
                "accept": "image/png,image/jpeg,image/jpg,image/svg+xml,image/webp"
            }),
            "favicon": forms.ClearableFileInput(attrs={
                "class": "form-control",
                "accept": "image/x-icon,image/png,image/svg+xml"
            }),
            "yearly_dues": forms.NumberInput(attrs={
                "class": "form-control",
                "step": "0.01",
                "min": "0"
            }),
            "minimum_age": forms.NumberInput(attrs={
                "class": "form-control",
                "min": "1",
                "max": "120"
            }),
            "past_member_age": forms.NumberInput(attrs={
                "class": "form-control",
                "min": "1",
                "max": "120"
            }),
            "primary_color": forms.TextInput(attrs={
                "class": "form-control",
                "type": "color"
            }),
            "accent_color": forms.TextInput(attrs={
                "class": "form-control",
                "type": "color"
            }),
            "theme_mode": forms.Select(attrs={"class": "form-select"}),
        }

    def clean_logo(self):
        logo = self.cleaned_data.get("logo")
        if logo:
            if logo.size > 2 * 1024 * 1024:
                raise forms.ValidationError("Logo must be under 2MB.")
            ext = logo.name.split(".")[-1].lower()
            if ext not in ["png", "jpg", "jpeg", "svg", "webp"]:
                raise forms.ValidationError("Logo must be PNG, JPG, SVG, or WEBP.")
        return logo

    def clean_favicon(self):
        favicon = self.cleaned_data.get("favicon")
        if favicon:
            if favicon.size > 1 * 1024 * 1024:
                raise forms.ValidationError("Favicon must be under 1MB.")
            ext = favicon.name.split(".")[-1].lower()
            if ext not in ["ico", "png", "svg"]:
                raise forms.ValidationError("Favicon must be ICO, PNG, or SVG.")
        return favicon

    def clean(self):
        cleaned_data = super().clean()
        min_age = cleaned_data.get("minimum_age")
        past_age = cleaned_data.get("past_member_age")

        if min_age and past_age and past_age <= min_age:
            raise forms.ValidationError(
                "Past member age must be greater than minimum age."
            )

        return cleaned_data


class DonationGroupForm(forms.ModelForm):
    """Form for creating and updating donation groups (Admin/Executive only)."""

    class Meta:
        model = DonationGroup
        fields = ["name", "description", "minimum_amount", "maximum_amount", "is_active"]
        widgets = {
            "name": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "e.g. G50, Diamond Members, Platinum Donors"
            }),
            "description": forms.Textarea(attrs={
                "class": "form-control",
                "rows": 3,
                "placeholder": "Describe who belongs in this group..."
            }),
            "minimum_amount": forms.NumberInput(attrs={
                "class": "form-control",
                "step": "0.01",
                "min": "0",
                "placeholder": "0.00"
            }),
            "maximum_amount": forms.NumberInput(attrs={
                "class": "form-control",
                "step": "0.01",
                "min": "0",
                "placeholder": "Leave blank for unlimited"
            }),
            "is_active": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }

    def clean(self):
        cleaned_data = super().clean()
        minimum = cleaned_data.get("minimum_amount")
        maximum = cleaned_data.get("maximum_amount")
        if minimum is not None and minimum < 0:
            self.add_error("minimum_amount", "Minimum amount cannot be negative.")
        if maximum is not None and minimum is not None and maximum < minimum:
            self.add_error("maximum_amount", "Maximum amount cannot be less than the minimum amount.")
        return cleaned_data


class DonationGroupMemberAssignForm(forms.Form):
    """Form for assigning a member to a donation group via the shared autocomplete."""

    member = forms.ModelChoiceField(
        queryset=exclude_admin_members(Member.objects.filter(status="ACTIVE")).order_by("full_name"),
        widget=AutocompleteSelectWidget(
            search_url_name="members:member_autocomplete_search",
            placeholder="Search member by name, no. or phone…",
        ),
        label="Member",
    )

    def __init__(self, *args, **kwargs):
        self.group = kwargs.pop("group", None)
        super().__init__(*args, **kwargs)
        self.fields["member"].widget.display_queryset = self.fields["member"].queryset

    def clean_member(self):
        member = self.cleaned_data["member"]
        if self.group and DonationGroupMembership.objects.filter(group=self.group, member=member).exists():
            raise forms.ValidationError(f"{member.full_name} is already in this group.")
        return member
