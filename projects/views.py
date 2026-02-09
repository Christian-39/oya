from django.shortcuts import render, redirect, get_object_or_404
from django.db.models import Sum
from .models import Project
from finance.models import Finance
from accounts.decorators import login_required, admin_required
from .forms import ProjectForm
from accounts.models import ExecutiveTenure
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
    form = ProjectForm()

    if request.method == 'POST':
        form = ProjectForm(request.POST)
        if form.is_valid():
            project = form.save(commit=False)

            current_tenure = ExecutiveTenure.objects.filter(is_active=True).first()

            # If project is completed, tag the tenure that completed it
            if project.status == 'completed':
                project.completed_by_tenure = current_tenure

            # If handed over, do NOT set completed tenure
            elif project.status == 'handed_over':
                project.completed_by_tenure = None

            # If ongoing/future/suspended/abandoned
            else:
                project.completed_by_tenure = None

            project.save()
            return redirect('projects_list')

    return render(request, 'projects/add_project.html', {'form': form})


@login_required
@admin_required
def edit_project(request, project_id):
    project = Project.objects.get(id=project_id)
    form = ProjectForm(instance=project)

    if request.method == 'POST':
        form = ProjectForm(request.POST, instance=project)
        if form.is_valid():
            project = form.save(commit=False)

            current_tenure = ExecutiveTenure.objects.filter(is_active=True).first()

            if project.status == 'completed':
                project.completed_by_tenure = current_tenure

            elif project.status == 'handed_over':
                project.completed_by_tenure = None

            project.save()
            return redirect('projects_list')

    return render(request, 'projects/edit_project.html', {'form': form})


# DELETE
@login_required
@admin_required
def delete_project(request, project_id):
    project = Project.objects.get(id=project_id)
    project.delete()
    return redirect('projects_list')
