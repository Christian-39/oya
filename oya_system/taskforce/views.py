from django.shortcuts import render, redirect
from .models import TaskForce, Motorcycle
from .forms import TaskForceForm, MotorcycleForm
from accounts.decorators import login_required, admin_required

@login_required
def taskforce_list(request):
    taskforce_members = TaskForce.objects.select_related('member').all()
    return render(request, 'taskforce/taskforce_list.html', {'taskforce_members': taskforce_members})


@login_required
@admin_required
def add_taskforce(request):
    if request.method == 'POST':
        form = TaskForceForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('taskforce_list')
    else:
        form = TaskForceForm()
    return render(request, 'taskforce/add_taskforce.html', {'form': form})


@login_required
def motorcycles_list(request):
    bikes = Motorcycle.objects.select_related('assigned_to__member').all()
    return render(request, 'taskforce/motorcycles_list.html', {'bikes': bikes})


@login_required
@admin_required
def add_motorcycle(request):
    if request.method == 'POST':
        form = MotorcycleForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('motorcycles_list')
    else:
        form = MotorcycleForm()
    return render(request, 'taskforce/add_motorcycle.html', {'form': form})
