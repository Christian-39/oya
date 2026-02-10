from django.shortcuts import render, redirect, get_object_or_404
from django.db.models import Sum
from .models import Contribution, Finance, Income
from .forms import ContributionForm, ExpenseForm, IncomeForm
from accounts.models import Member, Announcement, MeetingMinute
from accounts.decorators import login_required, admin_required
from django.db import IntegrityError
from django.contrib import messages
from datetime import datetime
from django.db.models import Q

YEARLY_DUES = 5000


@login_required
def income_list(request):
    member = Member.objects.get(id=request.session['member_id'])

    announcements_count = Announcement.objects.filter(is_active=True).count()
    minutes_count = MeetingMinute.objects.count()
    incomes = Income.objects.select_related('member').order_by('-date')
    contributions = Contribution.objects.select_related('member').order_by('-payment_date')

    total_income = incomes.aggregate(total=Sum('amount'))['total'] or 0
    total_contributions = contributions.aggregate(total=Sum('amount_paid'))['total'] or 0
    total_money = total_income + total_contributions

    return render(request, 'finance/income_list.html', {
        'incomes': incomes,
        'contributions': contributions,
        'total_income': total_income,
        'total_contributions': total_contributions,
        'total_money': total_money,
        'member': member,
        'announcements_count': announcements_count,
        'minutes_count': minutes_count,
    })


def add_income(request):
    if not request.session.get('member_id'):
        return redirect('login')
    member = Member.objects.get(id=request.session['member_id'])

    announcements_count = Announcement.objects.filter(is_active=True).count()
    minutes_count = MeetingMinute.objects.count()

    query = request.GET.get('q', '')
    found_member = None

    if query:
        found_member = Member.objects.filter(
            Q(full_name__icontains=query) |
            Q(serial_number__icontains=query)
        ).first()

    if request.method == 'POST':
        form = IncomeForm(request.POST)
        if form.is_valid():
            income = form.save(commit=False)
            income.recorded_by = member

            member_id = request.POST.get('member_id')
            if member_id:
                m = Member.objects.get(id=member_id)
                income.member = m
                income.sender_name = m.full_name  # 🔐 force correct data
                income.sender_id = m.serial_number  # 🔐 force correct data

            income.save()
            return redirect('income_list')
    else:
        initial_data = {}
        if found_member:
            initial_data = {
                'sender_name': found_member.full_name,
                'sender_id': found_member.serial_number,
            }
        form = IncomeForm(initial=initial_data)

    return render(request, 'finance/add_income.html', {
        'form': form,
        'query': query,
        'found_member': found_member,
        'member': member,
        'announcements_count': announcements_count,
        'minutes_count': minutes_count,
    })


@login_required
@admin_required
def add_contribution(request):
    member = Member.objects.get(id=request.session['member_id'])

    announcements_count = Announcement.objects.filter(is_active=True).count()
    minutes_count = MeetingMinute.objects.count()
    if request.method == 'POST':
        form = ContributionForm(request.POST)
        if form.is_valid():
            try:
                contribution = form.save(commit=False)
                contribution.recorded_by = Member.objects.get(id=request.session['member_id'])
                contribution.save()
                messages.success(request, "Contribution recorded successfully.")
                return redirect('contributions_list')
            except IntegrityError:
                messages.error(request, "This member has already paid dues for this year.")
    else:
        form = ContributionForm()

    return render(request, 'finance/add_contribution.html', {
        'form': form,
        'member': member,
        'announcements_count': announcements_count,
        'minutes_count': minutes_count,
    })


@login_required
def contributions_list(request):
    member = Member.objects.get(id=request.session['member_id'])

    announcements_count = Announcement.objects.filter(is_active=True).count()
    minutes_count = MeetingMinute.objects.count()
    contributions = Contribution.objects.select_related('member').order_by('-payment_date')
    return render(request, 'finance/contributions_list.html', {
        'contributions': contributions,
        'member': member,
        'announcements_count': announcements_count,
        'minutes_count': minutes_count,
    })


@login_required
def my_contributions(request):
    member = Member.objects.get(id=request.session['member_id'])

    announcements_count = Announcement.objects.filter(is_active=True).count()
    minutes_count = MeetingMinute.objects.count()

    contributions = Contribution.objects.filter(member=member)
    incomes = Income.objects.filter(member=member).order_by('-date')

    total_dues = contributions.aggregate(total=Sum('amount_paid'))['total'] or 0
    total_income = incomes.aggregate(total=Sum('amount'))['total'] or 0

    total_money = total_dues + total_income

    return render(request, 'finance/my_contributions.html', {
        'contributions': contributions,
        'incomes': incomes,
        'total_dues': total_dues,
        'total_income': total_income,
        'total_money': total_money,
        'member': member,
        'announcements_count': announcements_count,
        'minutes_count': minutes_count,
    })


@login_required
@admin_required
def add_expense(request):
    member = Member.objects.get(id=request.session['member_id'])

    announcements_count = Announcement.objects.filter(is_active=True).count()
    minutes_count = MeetingMinute.objects.count()
    if request.method == 'POST':
        form = ExpenseForm(request.POST)
        if form.is_valid():
            expense = form.save(commit=False)
            expense.recorded_by = Member.objects.get(id=request.session['member_id'])
            expense.type = 'expense'
            expense.save()
            return redirect('expenses_list')
    else:
        form = ExpenseForm()

    return render(request, 'finance/add_expenses.html', {
        'form': form,
        'member': member,
        'announcements_count': announcements_count,
        'minutes_count': minutes_count,
    })


@login_required
def expenses_list(request):
    member = Member.objects.get(id=request.session['member_id'])

    announcements_count = Announcement.objects.filter(is_active=True).count()
    minutes_count = MeetingMinute.objects.count()
    expenses = Finance.objects.filter(type='expense').order_by('-date')
    incomes = Income.objects.select_related('member').order_by('-date')
    contributions = Contribution.objects.select_related('member').order_by('-payment_date')
    total_income = incomes.aggregate(total=Sum('amount'))['total'] or 0
    total_contributions = contributions.aggregate(total=Sum('amount_paid'))['total'] or 0
    total_expenses = Finance.objects.filter(type='expense').aggregate(total=Sum('amount'))['total'] or 0

    total_money = total_contributions + total_income
    net_balance = total_money - total_expenses
    return render(request, 'finance/expenses_list.html', {
        'expenses': expenses,
        'contributions': contributions,
        'incomes': incomes,
        'total_expenses': total_expenses,
        'total_income': total_income,
        'net_balance': net_balance,
        'member': member,
        'announcements_count': announcements_count,
        'minutes_count': minutes_count,
    })


@login_required
def income_receipt(request, income_id):
    member = Member.objects.get(id=request.session['member_id'])

    announcements_count = Announcement.objects.filter(is_active=True).count()
    minutes_count = MeetingMinute.objects.count()
    income = Income.objects.select_related('member', 'recorded_by').get(id=income_id)
    return render(request, 'finance/income_receipt.html', {
        'income': income,
        'member': member,
        'announcements_count': announcements_count,
        'minutes_count': minutes_count,
    })


@login_required
def contribution_receipt(request, contribution_id):
    member = Member.objects.get(id=request.session['member_id'])

    announcements_count = Announcement.objects.filter(is_active=True).count()
    minutes_count = MeetingMinute.objects.count()
    contribution = Contribution.objects.select_related('member', 'recorded_by').get(id=contribution_id)
    return render(request, 'finance/contribution_receipt.html', {
        'contribution': contribution,
        'member': member,
        'announcements_count': announcements_count,
        'minutes_count': minutes_count,
    })


@login_required
def donation_list(request):
    member = Member.objects.get(id=request.session['member_id'])

    announcements_count = Announcement.objects.filter(is_active=True).count()
    minutes_count = MeetingMinute.objects.count()
    donation = Income.objects.select_related('member').order_by('-date')
    return render(request, 'finance/donation_list.html', {
        'donation': donation,
        'member': member,
        'announcements_count': announcements_count,
        'minutes_count': minutes_count,
    })


@login_required
@admin_required
def edit_contribution(request, contribution_id):
    member = Member.objects.get(id=request.session['member_id'])

    announcements_count = Announcement.objects.filter(is_active=True).count()
    minutes_count = MeetingMinute.objects.count()
    contribution = Contribution.objects.get(id=contribution_id)
    form = ContributionForm(instance=contribution)

    if request.method == 'POST':
        form = ContributionForm(request.POST, instance=contribution)
        if form.is_valid():
            form.save()
            return redirect('contributions_list')

    return render(request, 'finance/edit_contribution.html', {
        'form': form,
        'member': member,
        'announcements_count': announcements_count,
        'minutes_count': minutes_count,
    })


# DELETE
@login_required
@admin_required
def delete_contribution(request, contribution_id):
    contribution = Contribution.objects.get(id=contribution_id)
    contribution.delete()
    return redirect('contributions_list')


@login_required
@admin_required
def edit_expenses(request, expenses_id):
    member = Member.objects.get(id=request.session['member_id'])

    announcements_count = Announcement.objects.filter(is_active=True).count()
    minutes_count = MeetingMinute.objects.count()
    expenses = Finance.objects.get(id=expenses_id)

    if request.method == 'POST':
        form = ExpenseForm(request.POST, instance=expenses)
        if form.is_valid():
            form.save()
            return redirect('expenses_list')
    else:
        form = ExpenseForm(instance=expenses)

    return render(request, 'finance/edit_expenses.html', {
        'form': form,
        'expenses': expenses,
        'member': member,
        'announcements_count': announcements_count,
        'minutes_count': minutes_count,
    })


@login_required
@admin_required
def delete_expenses(request, expenses_id):
    expenses = Finance.objects.get(id=expenses_id)

    if request.method == 'POST':
        expenses.delete()
        return redirect('expenses_list')

    return render(request, 'finance/delete_expenses.html', {
        'expenses': expenses,
    })
