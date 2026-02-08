from django import forms
from .models import TaskForce, Motorcycle


class TaskForceForm(forms.ModelForm):
    class Meta:
        model = TaskForce
        fields = ['member', 'role_in_taskforce', 'phone_number', 'status']


class MotorcycleForm(forms.ModelForm):
    class Meta:
        model = Motorcycle
        fields = ['bike_number', 'plate_number', 'condition', 'assigned_to', 'status']
