from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from .models import Member, ExecutiveTenure
from django.contrib.auth.hashers import check_password, make_password
from .forms import PinLoginForm, ExecutiveTenureForm
import hashlib
from .forms import MemberForm
from .decorators import admin_required, login_required
from django.db.models import Sum
from taskforce.models import TaskForce
from django.db.models import Q
from .models import Executive
from cases.models import Case
from finance.models import Contribution, Income, Finance
from taskforce.models import Motorcycle
from decimal import Decimal
from django.utils.timezone import now


def hash_pin(pin: str) -> str:
    return hashlib.sha256(pin.encode()).hexdigest()


def login_view(request):
    if request.method == 'POST':
        form = PinLoginForm(request.POST)
        if form.is_valid():
            serial_number = form.cleaned_data['serial_number'].strip()
            pin = form.cleaned_data['pin'].strip()

            try:
                member = Member.objects.get(serial_number=serial_number)

                if not check_password(pin, member.password):
                    messages.error(request, "Invalid serial number or PIN.")
                    return redirect('login')

                # save session
                request.session['member_id'] = member.id
                request.session['member_role'] = member.role
                return redirect('dashboard')

            except Member.DoesNotExist:
                messages.error(request, "Invalid serial number or PIN.")
    else:
        form = PinLoginForm()

    return render(request, 'accounts/login.html', {'form': form})


def logout_view(request):
    request.session.flush()
    return redirect('login')


@login_required
def dashboard(request):
    member = Member.objects.get(id=request.session['member_id'])
    total_members = Member.objects.count()

    total_contributions = Contribution.objects.aggregate(total=Sum('amount_paid'))['total'] or 0
    total_income = Income.objects.aggregate(total=Sum('amount'))['total'] or 0
    total_expenses = Finance.objects.filter(type='expense').aggregate(total=Sum('amount'))['total'] or 0

    total_money = total_contributions + total_income
    net_balance = total_money - total_expenses

    total_motorcycles = Motorcycle.objects.count()
    total_cases = Case.objects.count()

    return render(request, 'accounts/dashboard.html', {
        'member': member,
        'total_income': total_income,
        'total_money': total_money,
        'total_expenses': total_expenses,
        'net_balance': net_balance,

        'total_members': total_members,
        'total_contributions': total_contributions,  # 👈 NOW REAL TOTAL INCOME
        'total_motorcycles': total_motorcycles,
        'total_cases': total_cases,
    })


@login_required
@admin_required
def admin_dashboard(request):
    total_members = Member.objects.count()
    total_executives = Member.objects.filter(role='executive').count()
    total_taskforce = TaskForce.objects.count()

    total_expense = Finance.objects.filter(type='expense').aggregate(total=Sum('amount'))['total'] or 0

    total_income = Income.objects.aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
    total_contributions = Contribution.objects.aggregate(total=Sum('amount_paid'))['total'] or Decimal('0.00')

    total_money = total_income + total_contributions

    return render(request, 'accounts/admin_dashboard.html', context={
        'total_members': total_members,
        'total_executives': total_executives,
        'total_taskforce': total_taskforce,
        'total_income': total_income,
        'total_expense': total_expense,
        'total_contributions': total_contributions,
        'total_money': total_money,
    })


@login_required
def members_list(request):
    query = request.GET.get('q', '')
    if query:
        members = Member.objects.filter(
            Q(full_name__icontains=query) |
            Q(serial_number__icontains=query) |
            Q(phone_number__icontains=query)
        )
    else:
        members = Member.objects.all().order_by('full_name')

    return render(request, 'accounts/members_list.html', {'members': members, 'query': query})


@login_required
def member_profile(request, member_id):
    member = Member.objects.get(id=member_id)
    return render(request, 'accounts/member_profile.html', {'member': member})


@login_required
def executives_list(request):
    executives = Executive.objects.select_related('member').order_by('position')
    return render(request, 'accounts/executives_list.html', {'executives': executives})


@login_required
@admin_required
def assign_executive(request):
    from django import forms

    class AssignExecutiveForm(forms.Form):
        member = forms.ModelChoiceField(queryset=Member.objects.all())
        position = forms.ChoiceField(choices=Executive.POSITION_CHOICES)

    if request.method == 'POST':
        form = AssignExecutiveForm(request.POST)
        if form.is_valid():
            member = form.cleaned_data['member']
            position = form.cleaned_data['position']

            # Remove old executive if position already taken
            Executive.objects.filter(position=position).delete()

            # Assign new executive
            Executive.objects.update_or_create(
                member=member,
                defaults={'position': position}
            )

            # Update member role & executive_position field
            member.role = 'executive'
            member.executive_position = position
            member.save()

            return redirect('executives_list')
    else:
        form = AssignExecutiveForm()

    return render(request, 'accounts/assign_executive.html', {'form': form})


@login_required
@admin_required
def add_tenure(request):
    if request.method == 'POST':
        form = ExecutiveTenureForm(request.POST)
        if form.is_valid():

            # Deactivate all previous tenures
            ExecutiveTenure.objects.update(is_active=False)

            tenure = form.save(commit=False)
            tenure.is_active = True
            tenure.save()

            return redirect('tenures_list')
    else:
        form = ExecutiveTenureForm()

    return render(request, 'accounts/add_tenure.html', {'form': form})


@login_required
@admin_required
def tenures_list(request):
    tenures = Executive.objects.select_related('member').order_by('-id')
    return render(request, 'accounts/tenures_list.html', {'tenures': tenures})


@login_required
@admin_required
def add_member(request):
    if request.method == 'POST':
        form = MemberForm(request.POST)
        if form.is_valid():
            member = form.save(commit=False)

            # Hash the PIN before saving
            raw_pin = form.cleaned_data.get('pin')  # or 'pin' if that’s your field name
            member.password = make_password(raw_pin)

            member.save()
            return redirect('members_list')
    else:
        form = MemberForm()

    return render(request, 'accounts/add_member.html', {'form': form})


@login_required
@admin_required
def edit_tenure(request, tenure_id):
    tenure = get_object_or_404(Executive, id=tenure_id)
    form = ExecutiveTenureForm(request.POST or None, instance=tenure)

    if request.method == 'POST' and form.is_valid():
        form.save()
        return redirect('tenures_list')

    return render(request, 'accounts/edit_tenure.html', {'form': form, 'tenure': tenure})


@login_required
@admin_required
def delete_tenure(request, tenure_id):
    tenure = get_object_or_404(Executive, id=tenure_id)

    if request.method == 'POST':
        tenure.delete()
        return redirect('tenures_list')

    return render(request, 'accounts/delete_tenure.html', {'tenure': tenure})

