from django.shortcuts import render, redirect
from .models import TaskForce, Motorcycle
from .forms import TaskForceForm, MotorcycleForm
from accounts.decorators import login_required, admin_required

from accounts.models import Announcement, MeetingMinute, Member


@login_required
def taskforce_list(request):
    member = Member.objects.get(id=request.session['member_id'])

    announcements_count = Announcement.objects.filter(is_active=True).count()
    minutes_count = MeetingMinute.objects.count()
    taskforce_members = TaskForce.objects.select_related('member').all()
    return render(request, 'taskforce/taskforce_list.html', {
        'taskforce_members': taskforce_members,
        'member': member,
        'announcements_count': announcements_count,
        'minutes_count': minutes_count,
    })


@login_required
@admin_required
def add_taskforce(request):
    member = Member.objects.get(id=request.session['member_id'])

    announcements_count = Announcement.objects.filter(is_active=True).count()
    minutes_count = MeetingMinute.objects.count()
    if request.method == 'POST':
        form = TaskForceForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('taskforce_list')
    else:
        form = TaskForceForm()
    return render(request, 'taskforce/add_taskforce.html', {
        'form': form,
        'member': member,
        'announcements_count': announcements_count,
        'minutes_count': minutes_count,
    })


@login_required
def motorcycles_list(request):
    member = Member.objects.get(id=request.session['member_id'])

    announcements_count = Announcement.objects.filter(is_active=True).count()
    minutes_count = MeetingMinute.objects.count()
    bikes = Motorcycle.objects.select_related('assigned_to__member').all()
    return render(request, 'taskforce/motorcycles_list.html', {
        'bikes': bikes,
        'member': member,
        'announcements_count': announcements_count,
        'minutes_count': minutes_count,
    })


@login_required
@admin_required
def add_motorcycle(request):
    member = Member.objects.get(id=request.session['member_id'])

    announcements_count = Announcement.objects.filter(is_active=True).count()
    minutes_count = MeetingMinute.objects.count()
    if request.method == 'POST':
        form = MotorcycleForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('motorcycles_list')
    else:
        form = MotorcycleForm()
    return render(request, 'taskforce/add_motorcycle.html', {
        'form': form,
        'member': member,
        'announcements_count': announcements_count,
        'minutes_count': minutes_count,
    })


@login_required
@admin_required
def edit_taskforce(request, taskforce_id):
    member = Member.objects.get(id=request.session['member_id'])

    announcements_count = Announcement.objects.filter(is_active=True).count()
    minutes_count = MeetingMinute.objects.count()
    taskforce = TaskForce.objects.get(id=taskforce_id)

    if request.method == 'POST':
        form = TaskForceForm(request.POST, instance=taskforce)
        if form.is_valid():
            form.save()
            return redirect('taskforce_list')
    else:
        form = TaskForceForm(instance=taskforce)

    return render(request, 'taskforce/edit_taskforce.html', {
        'form': form,
        'taskforce': taskforce,
        'member': member,
        'announcements_count': announcements_count,
        'minutes_count': minutes_count,
    })

@login_required
@admin_required
def delete_taskforce(request, taskforce_id):
    taskforce = TaskForce.objects.get(id=taskforce_id)

    if request.method == 'POST':
        taskforce.delete()
        return redirect('taskforce_list')

    return render(request, 'taskforce/delete_taskforce.html', {
        'taskforce': taskforce
    })


@login_required
@admin_required
def edit_motorcycle(request, motorcycle_id):
    member = Member.objects.get(id=request.session['member_id'])

    announcements_count = Announcement.objects.filter(is_active=True).count()
    minutes_count = MeetingMinute.objects.count()
    motorcycle = Motorcycle.objects.get(id=motorcycle_id)

    if request.method == 'POST':
        form = MotorcycleForm(request.POST, instance=motorcycle)
        if form.is_valid():
            form.save()
            return redirect('motorcycles_list')
    else:
        form = MotorcycleForm(instance=motorcycle)

    return render(request, 'taskforce/edit_motorcycle.html', {
        'form': form,
        'motorcycle': motorcycle,
        'member': member,
        'announcements_count': announcements_count,
        'minutes_count': minutes_count,
    })

@login_required
@admin_required
def delete_motorcycle(request, motorcycle_id):
    motorcycle = Motorcycle.objects.get(id=motorcycle_id)

    if request.method == 'POST':
        motorcycle.delete()
        return redirect('motorcycle_list')

    return render(request, 'taskforce/delete_motorcycle.html', {
        'motorcycle': motorcycle
    })
