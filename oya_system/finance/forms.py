from django import forms
from .models import Contribution, Finance, Income


class ContributionForm(forms.ModelForm):
    class Meta:
        model = Contribution
        fields = ['member', 'year', 'amount_paid', 'payment_date']


class IncomeForm(forms.ModelForm):
    class Meta:
        model = Income
        fields = ['title', 'sender_name', 'sender_id', 'amount']


class ExpenseForm(forms.ModelForm):
    class Meta:
        model = Finance
        fields = ['title', 'description', 'amount', 'date']
