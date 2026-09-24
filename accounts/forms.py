"""
Forms for OYA accounts.
"""
import re
from django import forms
from django.contrib.auth.forms import AuthenticationForm
from .models import User


class LoginForm(forms.Form):
    """Login form using serial number and PIN."""
    serial_number = forms.CharField(
        max_length=20,
        widget=forms.TextInput(attrs={
            "class": "form-control",
            "placeholder": "e.g., OYA-2026-0001",
            "autofocus": True,
            "autocomplete": "username"
        }),
        label="Serial Number"
    )
    pin = forms.CharField(
        max_length=6,
        widget=forms.PasswordInput(attrs={
            "class": "form-control",
            "placeholder": "Enter 6-digit PIN",
            "maxlength": "6",
            "inputmode": "numeric",
            "autocomplete": "current-password"
        }),
        label="PIN"
    )

    def clean_serial_number(self):
        serial = self.cleaned_data.get("serial_number")
        if serial:
            serial = serial.upper().strip()
            if not re.match(r"^OYA-\d{4}-\d{4}$", serial):
                raise forms.ValidationError(
                    "Invalid serial number format. Use: OYA-YYYY-XXXX (e.g., OYA-2026-0001)"
                )
        return serial

    def clean_pin(self):
        pin = self.cleaned_data.get("pin")
        if pin:
            if not pin.isdigit():
                raise forms.ValidationError("PIN must contain only digits.")
            if len(pin) != 6:
                raise forms.ValidationError("PIN must be exactly 6 digits.")
        return pin


class ChangePINForm(forms.Form):
    """Form for users to change their own PIN."""
    current_pin = forms.CharField(
        max_length=6,
        widget=forms.PasswordInput(attrs={
            "class": "form-control",
            "placeholder": "Enter current PIN",
            "maxlength": "6",
            "inputmode": "numeric"
        }),
        label="Current PIN"
    )
    new_pin = forms.CharField(
        max_length=6,
        min_length=6,
        widget=forms.PasswordInput(attrs={
            "class": "form-control",
            "placeholder": "Enter new 6-digit PIN",
            "maxlength": "6",
            "inputmode": "numeric"
        }),
        label="New PIN"
    )
    confirm_pin = forms.CharField(
        max_length=6,
        min_length=6,
        widget=forms.PasswordInput(attrs={
            "class": "form-control",
            "placeholder": "Confirm new PIN",
            "maxlength": "6",
            "inputmode": "numeric"
        }),
        label="Confirm PIN"
    )

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)

    def clean_current_pin(self):
        pin = self.cleaned_data.get("current_pin")
        if self.user and not self.user.check_pin(pin):
            raise forms.ValidationError("Current PIN is incorrect.")
        return pin

    def clean_new_pin(self):
        pin = self.cleaned_data.get("new_pin")
        if pin:
            if not pin.isdigit():
                raise forms.ValidationError("PIN must contain only digits.")
            if len(pin) != 6:
                raise forms.ValidationError("PIN must be exactly 6 digits.")
        return pin

    def clean(self):
        cleaned_data = super().clean()
        new_pin = cleaned_data.get("new_pin")
        confirm_pin = cleaned_data.get("confirm_pin")
        if new_pin and confirm_pin and new_pin != confirm_pin:
            raise forms.ValidationError("New PINs do not match.")
        return cleaned_data


class UserCreateForm(forms.ModelForm):
    """Form for creating a new user."""
    pin = forms.CharField(
        max_length=6,
        min_length=6,
        widget=forms.PasswordInput(attrs={
            "class": "form-control",
            "placeholder": "6-digit PIN",
            "maxlength": "6"
        }),
        label="PIN"
    )

    class Meta:
        model = User
        fields = ["serial_number", "full_name", "phone", "state", "role", "photo", "is_active"]
        widgets = {
            "serial_number": forms.TextInput(attrs={"class": "form-control", "placeholder": "OYA-2026-0001"}),
            "full_name": forms.TextInput(attrs={"class": "form-control", "placeholder": "Full Name"}),
            "phone": forms.TextInput(attrs={"class": "form-control", "placeholder": "Phone Number"}),
            "state": forms.TextInput(attrs={"class": "form-control", "placeholder": "State"}),
            "role": forms.Select(attrs={"class": "form-select"}),
            "photo": forms.FileInput(attrs={"class": "form-control"}),
            "is_active": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Default new users to ADMIN role
        self.fields["role"].initial = "ADMIN"

    def clean_serial_number(self):
        serial = self.cleaned_data.get("serial_number")
        if serial:
            serial = serial.upper().strip()
            if not re.match(r"^OYA-\d{4}-\d{4}$", serial):
                raise forms.ValidationError(
                    "Invalid format. Use: OYA-YYYY-XXXX"
                )
            if User.objects.filter(serial_number=serial).exists():
                raise forms.ValidationError("This serial number already exists.")
        return serial

    def clean_pin(self):
        pin = self.cleaned_data.get("pin")
        if pin:
            if not pin.isdigit():
                raise forms.ValidationError("PIN must contain only digits.")
            if len(pin) != 6:
                raise forms.ValidationError("PIN must be exactly 6 digits.")
        return pin

    def save(self, commit=True):
        user = super().save(commit=False)
        # Use set_pin() which properly sets the pin field
        user.set_pin(self.cleaned_data["pin"])
        # Ensure admin defaults are set (in case role was changed in form)
        if user.role == "ADMIN":
            user.is_staff = True
            user.is_superuser = True
        if commit:
            user.save()
        return user


class UserUpdateForm(forms.ModelForm):
    """Form for updating user details."""
    new_pin = forms.CharField(
        max_length=6,
        min_length=6,
        required=False,
        widget=forms.PasswordInput(attrs={
            "class": "form-control",
            "placeholder": "Leave blank to keep current PIN",
            "maxlength": "6"
        }),
        label="New PIN (optional)"
    )

    class Meta:
        model = User
        fields = ["full_name", "phone", "state", "role", "photo", "is_active"]
        widgets = {
            "full_name": forms.TextInput(attrs={"class": "form-control"}),
            "phone": forms.TextInput(attrs={"class": "form-control"}),
            "state": forms.TextInput(attrs={"class": "form-control"}),
            "role": forms.Select(attrs={"class": "form-select"}),
            "photo": forms.FileInput(attrs={"class": "form-control"}),
            "is_active": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }

    def clean_new_pin(self):
        pin = self.cleaned_data.get("new_pin")
        if pin:
            if not pin.isdigit():
                raise forms.ValidationError("PIN must contain only digits.")
            if len(pin) != 6:
                raise forms.ValidationError("PIN must be exactly 6 digits.")
        return pin

    def save(self, commit=True):
        user = super().save(commit=False)
        new_pin = self.cleaned_data.get("new_pin")
        if new_pin:
            # Use set_pin() which properly sets the pin field
            # and update session hash to prevent logout
            user.set_pin(new_pin)
        # Sync permissions with role changes
        if user.role == "ADMIN":
            user.is_staff = True
            user.is_superuser = True
        elif user.role == "EXECUTIVE":
            user.is_staff = True
            user.is_superuser = False
        else:  # FLOOR_MEMBER
            user.is_staff = False
            user.is_superuser = False
        if commit:
            user.save()
        return user


class FloorMemberProfileForm(forms.ModelForm):
    """Form for floor members to edit their own profile."""

    class Meta:
        model = User
        fields = ["phone", "state"]
        widgets = {
            "phone": forms.TextInput(attrs={"class": "form-control", "placeholder": "Phone Number"}),
            "state": forms.TextInput(attrs={"class": "form-control", "placeholder": "State"}),
        }


class PINResetForm(forms.Form):
    """Form for resetting a user's PIN (admin only)."""
    serial_number = forms.CharField(
        max_length=20,
        widget=forms.TextInput(attrs={
            "class": "form-control",
            "placeholder": "Enter serial number"
        }),
        label="Serial Number"
    )
    new_pin = forms.CharField(
        max_length=6,
        min_length=6,
        widget=forms.PasswordInput(attrs={
            "class": "form-control",
            "placeholder": "New 6-digit PIN",
            "maxlength": "6"
        }),
        label="New PIN"
    )
    confirm_pin = forms.CharField(
        max_length=6,
        min_length=6,
        widget=forms.PasswordInput(attrs={
            "class": "form-control",
            "placeholder": "Confirm 6-digit PIN",
            "maxlength": "6"
        }),
        label="Confirm PIN"
    )

    def clean_serial_number(self):
        serial = self.cleaned_data.get("serial_number")
        if serial:
            serial = serial.upper().strip()
            if not User.objects.filter(serial_number=serial).exists():
                raise forms.ValidationError("User with this serial number does not exist.")
        return serial

    def clean_new_pin(self):
        pin = self.cleaned_data.get("new_pin")
        if pin:
            if not pin.isdigit():
                raise forms.ValidationError("PIN must contain only digits.")
            if len(pin) != 6:
                raise forms.ValidationError("PIN must be exactly 6 digits.")
        return pin

    def clean(self):
        cleaned_data = super().clean()
        new_pin = cleaned_data.get("new_pin")
        confirm_pin = cleaned_data.get("confirm_pin")
        if new_pin and confirm_pin and new_pin != confirm_pin:
            raise forms.ValidationError("PINs do not match.")
        return cleaned_data
