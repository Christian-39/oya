from django.shortcuts import render, redirect
from .models import Case
from .forms import CaseForm
from accounts.decorators import login_required, admin_required

from accounts.models import Member, Announcement, MeetingMinute


@login_required
def cases_list(request):
    member = Member.objects.get(id=request.session['member_id'])

    announcements_count = Announcement.objects.filter(is_active=True).count()
    minutes_count = MeetingMinute.objects.count()
    cases = Case.objects.select_related('presented_by').all().order_by('-date_presented')
    return render(request, 'cases/cases_list.html', {
        'cases': cases,
        'member': member,
        'announcements_count': announcements_count,
        'minutes_count': minutes_count,
    })


@login_required
@admin_required
def add_case(request):
    member = Member.objects.get(id=request.session['member_id'])

    announcements_count = Announcement.objects.filter(is_active=True).count()
    minutes_count = MeetingMinute.objects.count()
    if request.method == 'POST':
        form = CaseForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('cases_list')
    else:
        form = CaseForm()
    return render(request, 'cases/add_case.html', {
        'form': form,
        'member': member,
        'announcements_count': announcements_count,
        'minutes_count': minutes_count,
    })


@login_required
@admin_required
def update_case_status(request, case_id):
    member = Member.objects.get(id=request.session['member_id'])

    announcements_count = Announcement.objects.filter(is_active=True).count()
    minutes_count = MeetingMinute.objects.count()
    case = Case.objects.get(id=case_id)
    if request.method == 'POST':
        status = request.POST.get('status')
        case.status = status
        case.save()
        return redirect('cases_list')
    return render(request, 'cases/update_case.html', {
        'case': case,
        'member': member,
        'announcements_count': announcements_count,
        'minutes_count': minutes_count,
    })
