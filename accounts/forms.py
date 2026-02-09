from django import forms
import re
from .models import ExecutiveTenure, Member


class ExecutiveTenureForm(forms.ModelForm):
    class Meta:
        model = ExecutiveTenure
        fields = ['name', 'start_year', 'end_year', 'is_active']

    def clean(self):
        cleaned = super().clean()
        self.instance.start_year = cleaned.get('start_year')
        self.instance.end_year = cleaned.get('end_year')
        self.instance.clean()
        return cleaned


class PinLoginForm(forms.Form):
    serial_number = forms.CharField(max_length=20, label="Serial Number")
    pin = forms.CharField(max_length=6, widget=forms.PasswordInput, label="6-digit PIN")

    def clean_pin(self):
        pin = self.cleaned_data.get('pin')
        if not re.fullmatch(r"\d{6}", pin):
            raise forms.ValidationError("PIN must be exactly 6 digits.")
        return pin


class MemberForm(forms.ModelForm):
    class Meta:
        model = Member
        fields = ['full_name', 'serial_number', 'phone_number', 'age', 'year_joined', 'password', 'role']