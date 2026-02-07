from django import forms
from .models import Project
from accounts.models import ExecutiveTenure
from finance.models import Finance


class ExecutiveTenureForm(forms.ModelForm):
    class Meta:
        model = ExecutiveTenure
        fields = ['name', 'start_year', 'end_year']


class ProjectForm(forms.ModelForm):
    class Meta:
        model = Project
        fields = "__all__"
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4}),
        }


class ProjectExpenseForm(forms.ModelForm):
    class Meta:
        model = Finance
        fields = ['project', 'title', 'amount', 'date']
