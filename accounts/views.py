from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django import forms

from .models import Member, ExecutiveTenure, Announcement, MeetingMinute
from .forms import PinLoginForm, ExecutiveTenureForm
import hashlib
from .forms import MemberForm, AnnouncementForm, MeetingMinuteForm
from .decorators import admin_required, login_required
from django.db.models import Sum
from taskforce.models import TaskForce
from django.db.models import Q
from .models import Executive
from cases.models import Case
from finance.models import Contribution, Income, Finance
from taskforce.models import Motorcycle
from decimal import Decimal
from django.contrib.auth.hashers import check_password
from django.utils.timezone import now

from projects.models import Project


def hash_pin(pin: str) -> str:
    return hashlib.sha256(pin.encode()).hexdigest()


def login_view(request):
    if request.method == 'POST':
        form = PinLoginForm(request.POST)
        if form.is_valid():
            serial_number = form.cleaned_data['serial_number']
            pin = form.cleaned_data['pin']

            try:
                member = Member.objects.get(serial_number=serial_number)

                if check_password(pin, member.password):
                    request.session['member_id'] = member.id
                    request.session['member_role'] = member.role
                    return redirect('dashboard')
                else:
                    messages.error(request, "Invalid serial number or PIN.")

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

    announcements_count = Announcement.objects.filter(is_active=True).count()
    minutes_count = MeetingMinute.objects.count()

    total_contributions = Contribution.objects.aggregate(total=Sum('amount_paid'))['total'] or 0
    total_income = Income.objects.aggregate(total=Sum('amount'))['total'] or 0
    total_expenses = Finance.objects.filter(type='expense').aggregate(total=Sum('amount'))['total'] or 0

    total_money = total_contributions + total_income
    net_balance = total_money - total_expenses

    total_motorcycles = Motorcycle.objects.count()
    total_cases = Case.objects.count()

    return render(request, 'accounts/dashboard.html', {
        'member': member,
        'announcements_count': announcements_count,
        'minutes_count': minutes_count,
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

    announcements_count = Announcement.objects.filter(is_active=True).count()
    minutes_count = MeetingMinute.objects.count()

    total_expense = Finance.objects.filter(type='expense').aggregate(total=Sum('amount'))['total'] or 0

    total_income = Income.objects.aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
    total_contributions = Contribution.objects.aggregate(total=Sum('amount_paid'))['total'] or Decimal('0.00')

    total_money = total_income + total_contributions

    total_motorcycles = Motorcycle.objects.count()
    total_cases = Case.objects.count()
    total_projects = Project.objects.count()

    return render(request, 'accounts/admin_dashboard.html', context={
        'total_members': total_members,
        'announcements_count': announcements_count,
        'minutes_count': minutes_count,
        'total_executives': total_executives,
        'total_taskforce': total_taskforce,
        'total_income': total_income,
        'total_expense': total_expense,
        'total_contributions': total_contributions,
        'total_money': total_money,
        'total_motorcycles': total_motorcycles,
        'total_cases': total_cases,
        'total_projects': total_projects,
    })


@login_required
def members_list(request):
    member = Member.objects.get(id=request.session['member_id'])

    announcements_count = Announcement.objects.filter(is_active=True).count()
    minutes_count = MeetingMinute.objects.count()
    query = request.GET.get('q', '')
    query = request.GET.get('q', '')

    if query:
        members = Member.objects.filter(
            Q(full_name__icontains=query) |
            Q(serial_number__icontains=query) |
            Q(phone_number__icontains=query)
        ).order_by('serial_number')  # ✅ order search results too
    else:
        members = Member.objects.all().order_by('serial_number')

    return render(request, 'accounts/members_list.html', {
        'members': members,
        'query': query,
        'member': member,
        'announcements_count': announcements_count,
        'minutes_count': minutes_count,
    })


@login_required
def member_profile(request, member_id):
    member = Member.objects.get(id=member_id)

    announcements_count = Announcement.objects.filter(is_active=True).count()
    minutes_count = MeetingMinute.objects.count()
    return render(request, 'accounts/member_profile.html', {
        'member': member,
        'announcements_count': announcements_count,
        'minutes_count': minutes_count,
    })


@login_required
def executives_list(request):
    member = Member.objects.get(id=request.session['member_id'])

    announcements_count = Announcement.objects.filter(is_active=True).count()
    minutes_count = MeetingMinute.objects.count()
    executives = Executive.objects.select_related('member').order_by('position')
    return render(request, 'accounts/executives_list.html', {
        'executives': executives,
        'member': member,
        'announcements_count': announcements_count,
        'minutes_count': minutes_count,
    })


@login_required
@admin_required
def assign_executive(request):
    member = Member.objects.get(id=request.session['member_id'])

    announcements_count = Announcement.objects.filter(is_active=True).count()
    minutes_count = MeetingMinute.objects.count()

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

    return render(request, 'accounts/assign_executive.html', {
        'form': form,
        'member': member,
        'announcements_count': announcements_count,
        'minutes_count': minutes_count,
    })


@login_required
@admin_required
def add_tenure(request):
    member = Member.objects.get(id=request.session['member_id'])

    announcements_count = Announcement.objects.filter(is_active=True).count()
    minutes_count = MeetingMinute.objects.count()
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

    return render(request, 'accounts/add_tenure.html', {
        'form': form,
        'member': member,
        'announcements_count': announcements_count,
        'minutes_count': minutes_count,
    })


@login_required
@admin_required
def tenures_list(request):
    member = Member.objects.get(id=request.session['member_id'])

    announcements_count = Announcement.objects.filter(is_active=True).count()
    minutes_count = MeetingMinute.objects.count()
    tenures = Executive.objects.select_related('member').order_by('-id')
    return render(request, 'accounts/tenures_list.html', {
        'tenures': tenures,
        'member': member,
        'announcements_count': announcements_count,
        'minutes_count': minutes_count,
    })


@login_required
@admin_required
def add_member(request):
    member = Member.objects.get(id=request.session['member_id'])

    announcements_count = Announcement.objects.filter(is_active=True).count()
    minutes_count = MeetingMinute.objects.count()
    if request.method == 'POST':
        form = MemberForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('members_list')
    else:
        form = MemberForm()

    return render(request, 'accounts/add_member.html', {
        'form': form,
        'member': member,
        'announcements_count': announcements_count,
        'minutes_count': minutes_count,
    })

@login_required
@admin_required
def edit_tenure(request, tenure_id):
    member = Member.objects.get(id=request.session['member_id'])

    announcements_count = Announcement.objects.filter(is_active=True).count()
    minutes_count = MeetingMinute.objects.count()
    tenure = get_object_or_404(Executive, id=tenure_id)
    form = ExecutiveTenureForm(request.POST or None, instance=tenure)

    if request.method == 'POST' and form.is_valid():
        form.save()
        return redirect('tenures_list')

    return render(request, 'accounts/edit_tenure.html', {
        'form': form,
        'tenure': tenure,
        'member': member,
        'announcements_count': announcements_count,
        'minutes_count': minutes_count,
    })


@login_required
@admin_required
def delete_tenure(request, tenure_id):
    tenure = get_object_or_404(Executive, id=tenure_id)

    if request.method == 'POST':
        tenure.delete()
        return redirect('tenures_list')

    return render(request, 'accounts/delete_tenure.html', {'tenure': tenure})


@login_required
def announcements_list(request):
    member = Member.objects.get(id=request.session['member_id'])

    announcements_count = Announcement.objects.filter(is_active=True).count()
    minutes_count = MeetingMinute.objects.count()
    announcements = Announcement.objects.filter(is_active=True).order_by('-created_at')
    return render(request, 'accounts/announcements_list.html', {
        'announcements': announcements,
        'member': member,
        'announcements_count': announcements_count,
        'minutes_count': minutes_count,
    })



@admin_required
@login_required
def add_announcement(request):
    member = Member.objects.get(id=request.session['member_id'])

    announcements_count = Announcement.objects.filter(is_active=True).count()
    minutes_count = MeetingMinute.objects.count()
    if request.method == 'POST':
        form = AnnouncementForm(request.POST)
        if form.is_valid():
            ann = form.save(commit=False)
            ann.recorded_by = Member.objects.get(id=request.session['member_id'])
            ann.save()
            return redirect('announcements_list')
    else:
        form = AnnouncementForm()
    return render(request, 'accounts/add_announcement.html', {
        'form': form,
        'member': member,
        'announcements_count': announcements_count,
        'minutes_count': minutes_count,
    })


@login_required
def minutes_list(request):
    member = Member.objects.get(id=request.session['member_id'])

    announcements_count = Announcement.objects.filter(is_active=True).count()
    minutes_count = MeetingMinute.objects.count()
    minutes = MeetingMinute.objects.order_by('-meeting_date')
    return render(request, 'accounts/minutes_list.html', {
        'minutes': minutes,
        'member': member,
        'announcements_count': announcements_count,
        'minutes_count': minutes_count,
    })


@login_required
@admin_required
def add_minutes(request):
    member = Member.objects.get(id=request.session['member_id'])

    announcements_count = Announcement.objects.filter(is_active=True).count()
    minutes_count = MeetingMinute.objects.count()
    if request.method == 'POST':
        form = MeetingMinuteForm(request.POST)
        if form.is_valid():
            minute = form.save(commit=False)
            minute.recorded_by = Member.objects.get(id=request.session['member_id'])
            minute.save()
            return redirect('minutes_list')
    else:
        form = MeetingMinuteForm()
    return render(request, 'accounts/add_minutes.html', {
        'form': form,
        'member': member,
        'announcements_count': announcements_count,
        'minutes_count': minutes_count,
    })

@login_required
@admin_required
def edit_announcement(request, announcement_id):
    member = Member.objects.get(id=request.session['member_id'])

    announcements_count = Announcement.objects.filter(is_active=True).count()
    minutes_count = MeetingMinute.objects.count()
    announcement = Announcement.objects.get(id=announcement_id)

    if request.method == 'POST':
        form = AnnouncementForm(request.POST, instance=announcement)
        if form.is_valid():
            form.save()
            return redirect('announcements_list')
    else:
        form = AnnouncementForm(instance=announcement)

    return render(request, 'accounts/edit_announcement.html', {
        'form': form,
        'announcement': announcement,
        'member': member,
        'announcements_count': announcements_count,
        'minutes_count': minutes_count,
    })

@login_required
@admin_required
def delete_announcement(request, announcement_id):
    announcement = Announcement.objects.get(id=announcement_id)

    if request.method == 'POST':
        announcement.delete()
        return redirect('announcements_list')

    return render(request, 'accounts/delete_announcement.html', {
        'announcement': announcement
    })


# ===== MEETING MINUTES =====
@login_required
@admin_required
def edit_minutes(request, minutes_id):
    member = Member.objects.get(id=request.session['member_id'])

    announcements_count = Announcement.objects.filter(is_active=True).count()
    minutes_count = MeetingMinute.objects.count()
    minute = MeetingMinute.objects.get(id=minutes_id)

    if request.method == 'POST':
        form = MeetingMinuteForm(request.POST, instance=minute)
        if form.is_valid():
            form.save()
            return redirect('minutes_list')
    else:
        form = MeetingMinuteForm(instance=minute)

    return render(request, 'accounts/edit_minutes.html', {
        'form': form,
        'minute': minute,
        'member': member,
        'announcements_count': announcements_count,
        'minutes_count': minutes_count,
    })


@login_required
@admin_required
def delete_minutes(request, minutes_id):
    minute = MeetingMinute.objects.get(id=minutes_id)

    if request.method == 'POST':
        minute.delete()
        return redirect('minutes_list')

    return render(request, 'accounts/delete_minutes.html', {
        'minute': minute
    })


 #===== MEETING MINUTES =====
@login_required
@admin_required
def edit_executive(request, executive_id):
    member = Member.objects.get(id=request.session['member_id'])

    announcements_count = Announcement.objects.filter(is_active=True).count()
    minutes_count = MeetingMinute.objects.count()
    executive = Executive.objects.get(id=executive_id)

    if request.method == 'POST':
        form = ExecutiveTenureForm(request.POST, instance=executive)
        if form.is_valid():
            form.save()
            return redirect('executive_list')
    else:
        form = ExecutiveTenureForm(instance=executive)

    return render(request, 'accounts/edit_executive.html', {
        'form': form,
        'executive': executive,
        'member': member,
        'announcements_count': announcements_count,
        'minutes_count': minutes_count,
    })


@login_required
@admin_required
def delete_executive(request, executive_id):
    executive = Executive.objects.get(id=executive_id)

    if request.method == 'POST':
        executive.delete()
        return redirect('executive_list')

    return render(request, 'accounts/delete_executive.html', {
        'executive': executive
    })

@login_required
@admin_required
def edit_member(request, member_id):
    members = Member.objects.get(id=request.session['member_id'])

    announcements_count = Announcement.objects.filter(is_active=True).count()
    minutes_count = MeetingMinute.objects.count()
    member = Member.objects.get(id=member_id)

    if request.method == 'POST':
        form = MemberForm(request.POST, instance=member)
        if form.is_valid():
            form.save()
            return redirect('members_list')
    else:
        form = MemberForm(instance=member)

    return render(request, 'accounts/edit_member.html', {
        'form': form,
        'members': members,
        'member': member,
        'announcements_count': announcements_count,
        'minutes_count': minutes_count,
    })


@login_required
@admin_required
def delete_member(request, member_id):
    member = Member.objects.get(id=member_id)

    if request.method == 'POST':
        member.delete()
        return redirect('member_list')

    return render(request, 'accounts/delete_member.html', {
        'member': member
    })
