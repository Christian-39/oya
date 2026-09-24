"""
Views for OYA projects.
"""
import logging
from dashboard.services import invalidate_dashboard_cache
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q, Count
from auditlogs.services import log_action
from .models import Project
from .forms import ProjectForm

logger = logging.getLogger("oya")


@login_required
def project_list(request):
    """List all projects with search, filter, and pagination."""
    queryset = Project.objects.all()

    search_term = request.GET.get("search", "")
    if search_term:
        queryset = queryset.filter(
            Q(title__icontains=search_term) |
            Q(description__icontains=search_term)
        )

    status_filter = request.GET.get("status", "")
    if status_filter:
        queryset = queryset.filter(status=status_filter)

    paginator = Paginator(queryset, 25)
    page = request.GET.get("page", 1)
    projects = paginator.get_page(page)

    # Statistics — single query
    stats = Project.objects.aggregate(
        future=Count("id", filter=Q(status="FUTURE")),
        at_hand=Count("id", filter=Q(status="AT_HAND")),
        finished=Count("id", filter=Q(status="FINISHED")),
        total=Count("id"),
    )

    context = {
        "projects": projects,
        "stats": stats,
        "search_term": search_term,
        "status_filter": status_filter,
        "status_choices": Project.STATUS_CHOICES,
    }
    return render(request, "projects/project_list.html", context)


@login_required
def project_detail(request, pk):
    """Display project details with fundraising data."""
    project = get_object_or_404(Project, pk=pk)
    
    fundraising_data = None
    if project.enable_fundraising:
        from project_donations.models import Donation
        from django.db.models import Sum
        
        confirmed = Donation.objects.filter(
            project=project, status="CONFIRMED"
        ).select_related("member", "outside_donor", "recorded_by").order_by("-donation_date")
        
        member_donations = confirmed.filter(donor_type="MEMBER")
        outside_donations = confirmed.filter(donor_type="OUTSIDE")
        
        total_donors = confirmed.values("member", "outside_donor").distinct().count()
        
        top_member_donors = member_donations.values(
            "member__id", "member__full_name", "member__photo"
        ).annotate(total=Sum("amount")).order_by("-total")[:5]
        
        top_outside_donors = outside_donations.values(
            "outside_donor__id", "outside_donor__full_name", "outside_donor__profile_picture"
        ).annotate(total=Sum("amount")).order_by("-total")[:5]
        
        top_inviters = confirmed.filter(
            invited_by__isnull=False
        ).values(
            "invited_by__id", "invited_by__full_name", "invited_by__photo"
        ).annotate(total=Sum("amount")).order_by("-total")[:5]
        
        fundraising_data = {
            "total_donors": total_donors,
            "member_donations_total": project.total_member_donations,
            "outside_donations_total": project.total_outside_donations,
            "total_donations_recorded": confirmed.count(),
            "top_member_donors": list(top_member_donors),
            "top_outside_donors": list(top_outside_donors),
            "top_inviters": list(top_inviters),
            "recent_donations": confirmed[:10],
        }
    
    return render(request, "projects/project_detail.html", {
        "project": project,
        "fundraising_data": fundraising_data,
    })



@login_required
def project_create(request):
    """Create a new project."""
    if not request.user.has_executive_access():
        messages.error(request, "Executive access required.")
        return redirect("projects:project_list")

    if request.method == "POST":
        form = ProjectForm(request.POST)
        if form.is_valid():
            project = form.save()
            log_action(
                user=request.user,
                action="CREATE",
                object_type="Project",
                object_id=project.id,
                ip_address=getattr(request, "client_ip", ""),
                description=f"Created project: {project.title}"
            )
            messages.success(request, f"Project '{project.title}' created successfully.")
            invalidate_dashboard_cache()
            return redirect("projects:project_list")
        else:
            for error in form.errors.values():
                messages.error(request, error)
    else:
        form = ProjectForm()

    return render(request, "projects/project_form.html", {
        "form": form,
        "title": "Create Project",
        "action": "Create"
    })


@login_required
def project_update(request, pk):
    """Update an existing project."""
    if not request.user.has_executive_access():
        messages.error(request, "Executive access required.")
        return redirect("projects:project_list")

    project = get_object_or_404(Project, pk=pk)

    if request.method == "POST":
        form = ProjectForm(request.POST, instance=project)
        if form.is_valid():
            form.save()
            log_action(
                user=request.user,
                action="UPDATE",
                object_type="Project",
                object_id=project.id,
                ip_address=getattr(request, "client_ip", ""),
                description=f"Updated project: {project.title}"
            )
            messages.success(request, "Project updated successfully.")
            invalidate_dashboard_cache()
            return redirect("projects:project_list")
        else:
            for error in form.errors.values():
                messages.error(request, error)
    else:
        form = ProjectForm(instance=project)

    return render(request, "projects/project_form.html", {
        "form": form,
        "title": "Update Project",
        "action": "Update",
        "project": project
    })


@login_required
def project_delete(request, pk):
    """Delete a project."""
    if not request.user.has_admin_access():
        messages.error(request, "Admin access required.")
        return redirect("projects:project_list")

    project = get_object_or_404(Project, pk=pk)

    if request.method == "POST":
        title = project.title
        project.delete()
        log_action(
            user=request.user,
            action="DELETE",
            object_type="Project",
            object_id=pk,
            ip_address=getattr(request, "client_ip", ""),
            description=f"Deleted project: {title}"
        )
        messages.success(request, f"Project '{title}' deleted.")
        invalidate_dashboard_cache()
        return redirect("projects:project_list")

    return render(request, "projects/project_confirm_delete.html", {"project": project})