"""
Forms for OYA notifications.
"""
from django import forms
from .models import Notification


class NotificationForm(forms.ModelForm):
    """Form for creating notifications."""

    class Meta:
        model = Notification
        fields = ["title", "message", "notification_type", "recipient", "is_global"]
        widgets = {
            "title": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Notification title"
            }),
            "message": forms.Textarea(attrs={
                "class": "form-control",
                "rows": 4,
                "placeholder": "Notification message..."
            }),
            "notification_type": forms.Select(attrs={"class": "form-select"}),
            "recipient": forms.Select(attrs={"class": "form-select"}),
            "is_global": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }

    def clean(self):
        cleaned_data = super().clean()
        is_global = cleaned_data.get("is_global")
        recipient = cleaned_data.get("recipient")

        if not is_global and not recipient:
            raise forms.ValidationError(
                "Either select a recipient or mark as global notification."
            )

        return cleaned_data
