from django.shortcuts import render, redirect, get_object_or_404
from django.db.models import Sum
from .models import Project
from finance.models import Finance
from accounts.decorators import login_required, admin_required
from .forms import ProjectForm
from accounts.models import Member
from django.contrib import messages


@login_required
def projects_list(request):
    projects = Project.objects.select_related('started_by_tenure', 'completed_by_tenure')
    return render(request, 'projects/projects_list.html', {'projects': projects})


@login_required
def project_detail(request, project_id):
    project = get_object_or_404(Project, id=project_id)
    expenses = Finance.objects.filter(project=project, type='expense')
    total_spent = expenses.aggregate(total=Sum('amount'))['total'] or 0

    return render(request, 'projects/project_detail.html', {
        'project': project,
        'expenses': expenses,
        'total_spent': total_spent
    })


@login_required
@admin_required
def add_project(request):
    if request.method == 'POST':
        form = ProjectForm(request.POST)
        if form.is_valid():
            project = form.save(commit=False)
            project.created_by = Member.objects.get(id=request.session['member_id'])
            project.save()
            return redirect('projects_list')
    else:
        form = ProjectForm()
    return render(request, 'projects/add_project.html', {'form': form})


def edit_project(request, pk):
    project = get_object_or_404(Project, pk=pk)
    if request.method == 'POST':
        form = ProjectForm(request.POST, request.FILES, instance=project)
        if form.is_valid():
            form.save()
            messages.success(request, "Project updated successfully ✨")
            return redirect('projects_list')
    else:
        form = ProjectForm(instance=project)
    return render(request, 'projects/edit.html', {'form': form, 'project': project})
