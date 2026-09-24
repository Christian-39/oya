"""
Forms for OYA members.
"""
import random
import string
from django import forms
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from .models import Member, Clan, NIGERIAN_STATES


class MemberForm(forms.ModelForm):
    """Form for creating members — includes PIN for login account creation."""

    # PIN field is NOT a model field — it's a form-only field for User creation
    pin = forms.CharField(
        max_length=6,
        min_length=6,
        required=False,
        label="PIN (6 digits)",
        widget=forms.PasswordInput(attrs={
            "class": "form-input",
            "placeholder": "Leave blank to auto-generate",
            "maxlength": "6",
            "inputmode": "numeric"
        }),
        help_text="6-digit PIN for login. Leave blank to auto-generate."
    )

    # Location fields
    is_abroad = forms.BooleanField(
        required=False,
        label="Living Abroad?",
        widget=forms.CheckboxInput(attrs={"class": "form-check-input", "id": "id_is_abroad"})
    )

    nigerian_state = forms.ChoiceField(
        choices=[("", "-- Select State --")] + NIGERIAN_STATES,
        required=False,
        label="Nigerian State",
        widget=forms.Select(attrs={
            "class": "form-select",
            "id": "id_nigerian_state",
        })
    )

    abroad_country = forms.CharField(
        max_length=100,
        required=False,
        label="Country (if abroad)",
        widget=forms.TextInput(attrs={
            "class": "form-input",
            "placeholder": "Enter country name (e.g., USA, UK, Canada)",
            "id": "id_abroad_country",
        })
    )

    # Year joined - allow administrators to choose when member joined
    year_joined = forms.IntegerField(
        min_value=2020,
        max_value=timezone.now().year,
        required=True,
        label="Year Joined",
        widget=forms.NumberInput(attrs={
            "class": "form-input",
            "placeholder": "e.g., 2022",
            "min": "2020",
            "max": str(timezone.now().year),
        }),
        help_text="The year this member joined the association. Dues tracking starts from this year."
    )

    class Meta:
        model = Member
        # NOTE: 'pin' is NOT in Meta.fields because it's not a Member model field!
        # It's a form-only field used to create the User account
        fields = [
            "serial_number", "full_name", "phone", "age",
            "umu_nna_clan", "photo", "is_abroad", "nigerian_state",
            "abroad_country", "year_joined", "status"
        ]
        widgets = {
            "serial_number": forms.TextInput(attrs={
                "class": "form-input",
                "placeholder": "OYA-2026-0001"
            }),
            "full_name": forms.TextInput(attrs={
                "class": "form-input",
                "placeholder": "Enter full name"
            }),
            "phone": forms.TextInput(attrs={
                "class": "form-input",
                "placeholder": "08012345678"
            }),
            "age": forms.NumberInput(attrs={
                "class": "form-input",
                "min": "18",
                "max": "55",
                "placeholder": "18-55"
            }),
            "umu_nna_clan": forms.Select(attrs={
                "class": "form-select",
                "data-placeholder": "Select your clan..."
            }),
            "photo": forms.FileInput(attrs={"class": "form-input"}),
            "status": forms.Select(attrs={"class": "form-select"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not Clan.objects.exists():
            self._seed_clans()
        self.fields["umu_nna_clan"].queryset = Clan.objects.all().order_by("name")
        self.fields["umu_nna_clan"].empty_label = "-- Select Clan --"

        # Set default year_joined to current year for new members
        if not self.instance or not self.instance.pk:
            self.fields["year_joined"].initial = timezone.now().year

        if self.instance and self.instance.pk:
            if self.instance.is_abroad:
                self.fields["abroad_country"].initial = self.instance.state_or_abroad
            else:
                state_value = self.instance.state_or_abroad
                if state_value in [s[0] for s in NIGERIAN_STATES]:
                    self.fields["nigerian_state"].initial = state_value

    def _seed_clans(self):
        default_clans = [
            "Umu Onoja", "Umu Osede", "Umu Edoga",
            "Umu Nna Ose", "Umu Igwurube", "Others",
        ]
        for clan_name in default_clans:
            Clan.objects.get_or_create(name=clan_name)

    def clean_age(self):
        age = self.cleaned_data.get("age")
        if age is not None:
            if age < 18:
                raise forms.ValidationError("Age must be at least 18 years old.")
            if age > 55:
                raise forms.ValidationError("Age must not exceed 55 years old.")
        return age

    def clean_pin(self):
        pin = self.cleaned_data.get("pin")
        if pin:
            if not pin.isdigit():
                raise forms.ValidationError("PIN must contain only digits.")
            if len(pin) != 6:
                raise forms.ValidationError("PIN must be exactly 6 digits.")
        return pin

    def clean_year_joined(self):
        year_joined = self.cleaned_data.get("year_joined")
        current_year = timezone.now().year
        if year_joined:
            if year_joined < 2020:
                raise forms.ValidationError("Join year cannot be before platform creation (2020).")
            if year_joined > current_year:
                raise forms.ValidationError("Join year cannot be in the future.")
        return year_joined

    def clean(self):
        cleaned_data = super().clean()
        is_abroad = cleaned_data.get("is_abroad")
        nigerian_state = cleaned_data.get("nigerian_state")
        abroad_country = cleaned_data.get("abroad_country")

        if is_abroad:
            if not abroad_country:
                self.add_error("abroad_country", "Please enter the country name.")
            cleaned_data["state_or_abroad"] = abroad_country
        else:
            if not nigerian_state:
                self.add_error("nigerian_state", "Please select a Nigerian state.")
            cleaned_data["state_or_abroad"] = nigerian_state

        return cleaned_data

    def save(self, commit=True):
        """Save member and create corresponding User account with PIN."""
        from accounts.models import User

        # Save Member first (using the old working logic)
        instance = super().save(commit=False)
        instance.is_abroad = self.cleaned_data.get("is_abroad", False)
        instance.state_or_abroad = self.cleaned_data.get("state_or_abroad", "")

        if commit:
            instance.save()

            # Get or generate PIN
            pin = self.cleaned_data.get("pin")
            if not pin:
                pin = ''.join(random.choices(string.digits, k=6))

            # Create or update User account
            try:
                user = User.objects.get(serial_number=instance.serial_number)
                user.full_name = instance.full_name
                user.phone = instance.phone
                user.state = instance.state_or_abroad
                user.is_active = instance.status == "ACTIVE"
                # SYNC: year_joined from Member to User
                user.year_joined = instance.year_joined
                # SYNC PHOTO from Member to User
                if instance.photo:
                    user.photo = instance.photo
                # FIX Issue 1 & 2: Ensure floor members are not staff/superuser
                user.is_staff = False
                user.is_superuser = False
                user.set_pin(pin)  # Use custom set_pin(), not set_password()
                user.save()
            except User.DoesNotExist:
                user = User(
                    serial_number=instance.serial_number,
                    full_name=instance.full_name,
                    phone=instance.phone,
                    state=instance.state_or_abroad,
                    role="FLOOR_MEMBER",
                    is_active=instance.status == "ACTIVE",
                    year_joined=instance.year_joined,
                    # FIX Issue 1 & 2: Explicitly set staff/superuser to False
                    is_staff=False,
                    is_superuser=False,
                )
                # SYNC PHOTO from Member to User
                if instance.photo:
                    user.photo = instance.photo
                user.set_pin(pin)  # Use custom set_pin(), not set_password()
                user.save()

            # Store PIN for one-time display to admin
            instance._generated_pin = pin

        return instance


class MemberUpdateForm(MemberForm):
    """Form for updating existing members."""

    pin = forms.CharField(
        max_length=6,
        min_length=6,
        required=False,
        label="PIN (6 digits)",
        widget=forms.PasswordInput(attrs={
            "class": "form-input",
            "placeholder": "Leave blank to keep current PIN",
            "maxlength": "6",
            "inputmode": "numeric"
        }),
        help_text="Leave blank to keep the current PIN unchanged."
    )

    def save(self, commit=True):
        """Update member and sync User account. Only update PIN if provided."""
        from accounts.models import User

        instance = super(MemberForm, self).save(commit=False)
        instance.is_abroad = self.cleaned_data.get("is_abroad", False)
        instance.state_or_abroad = self.cleaned_data.get("state_or_abroad", "")

        if commit:
            instance.save()

            try:
                user = User.objects.get(serial_number=instance.serial_number)
                user.full_name = instance.full_name
                user.phone = instance.phone
                user.state = instance.state_or_abroad
                user.is_active = instance.status == "ACTIVE"
                # SYNC: year_joined from Member to User
                user.year_joined = instance.year_joined
                # SYNC PHOTO from Member to User
                if instance.photo:
                    user.photo = instance.photo
                # FIX Issue 1 & 2: Ensure floor members are not staff/superuser
                user.is_staff = False
                user.is_superuser = False

                pin = self.cleaned_data.get("pin")
                if pin:
                    user.set_pin(pin)
                    instance._updated_pin = pin

                user.save()
            except User.DoesNotExist:
                pin = self.cleaned_data.get("pin") or ''.join(random.choices(string.digits, k=6))
                user = User(
                    serial_number=instance.serial_number,
                    full_name=instance.full_name,
                    phone=instance.phone,
                    state=instance.state_or_abroad,
                    role="FLOOR_MEMBER",
                    is_active=instance.status == "ACTIVE",
                    year_joined=instance.year_joined,
                    # FIX Issue 1 & 2: Explicitly set staff/superuser to False
                    is_staff=False,
                    is_superuser=False,
                )
                # SYNC PHOTO from Member to User
                if instance.photo:
                    user.photo = instance.photo
                user.set_pin(pin)
                user.save()
                instance._generated_pin = pin

        return instance


class MemberRemoveForm(forms.ModelForm):
    """Form for removing a member with reason."""

    class Meta:
        model = Member
        fields = ["removal_reason", "offense_committed"]
        widgets = {
            "removal_reason": forms.Textarea(attrs={
                "class": "form-textarea",
                "rows": 4,
                "placeholder": "Enter reason for removal..."
            }),
            "offense_committed": forms.Textarea(attrs={
                "class": "form-textarea",
                "rows": 4,
                "placeholder": "Describe offense committed (if any)..."
            }),
        }


class ClanForm(forms.ModelForm):
    """Form for creating clans."""

    class Meta:
        model = Clan
        fields = ["name"]
        widgets = {
            "name": forms.TextInput(attrs={
                "class": "form-input",
                "placeholder": "Enter clan name"
            }),
        }
