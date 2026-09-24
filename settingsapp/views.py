"""
Views for OYA system settings.
"""
import logging
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.db.models import Q, Count
from auditlogs.services import log_request_action
from accounts.models import User
from members.models import Clan, Member
from core.utils import paginate_queryset, build_search_query
from .models import SystemSettings, DonationGroup, DonationGroupMembership
from .forms import SystemSettingsForm, DonationGroupForm, DonationGroupMemberAssignForm

logger = logging.getLogger("oya")


@login_required
def settings_view(request):
    """View and update system settings."""
    if not request.user.has_executive_access():
        messages.error(request, "Admin access required.")
        return redirect("dashboard:index")

    settings_obj = SystemSettings.load()

    if request.method == "POST":
        form = SystemSettingsForm(request.POST, request.FILES, instance=settings_obj)
        if form.is_valid():
            form.save()
            log_request_action(
                request,
                action="UPDATE",
                object_type="SystemSettings",
                object_id=settings_obj.id,
                description="Updated system settings"
            )
            messages.success(request, "System settings updated successfully.")
            return redirect("settingsapp:settings")
        else:
            for error_list in form.errors.values():
                for error in error_list:
                    messages.error(request, error)
    else:
        form = SystemSettingsForm(instance=settings_obj)

    # Get ALL users (not just admin/executive) for the Users & Access tab
    all_users = User.objects.all().order_by("-date_joined")

    # Get ALL members for the Members Management tab
    all_members = Member.objects.select_related("umu_nna_clan").all().order_by("-created_at")

    # Get member statistics
    member_stats = {
        "total": Member.objects.count(),
        "active": Member.objects.filter(status="ACTIVE").count(),
        "past": Member.objects.filter(status="PAST_MEMBER").count(),
        "removed": Member.objects.filter(status="REMOVED").count(),
    }

    # Get all clans with member counts for Clan Management tab
    clans = Clan.objects.annotate(member_count=Count("members")).order_by("name")

    return render(request, "settingsapp/settings.html", {
        "form": form,
        "settings": settings_obj,
        "all_users": all_users,
        "all_members": all_members,
        "member_stats": member_stats,
        "clans": clans,
    })


# ═══════════════════════════════════════════════════════════════
# DONATION GROUPS (Feature 1, 2, 3)
# ═══════════════════════════════════════════════════════════════

@login_required
def donation_group_list(request):
    """List all donation groups with search, filter, and pagination.
    
    Visible to ALL authenticated users. Management actions restricted
    to Admin/Executive via the can_manage flag in the template.
    """
    queryset = DonationGroup.objects.annotate(
        members_count=Count("memberships", distinct=True)
    ).order_by("name")

    search_term = request.GET.get("search", "")
    if search_term:
        queryset = queryset.filter(build_search_query(["name", "description"], search_term))

    status_filter = request.GET.get("status", "")
    if status_filter == "ACTIVE":
        queryset = queryset.filter(is_active=True)
    elif status_filter == "INACTIVE":
        queryset = queryset.filter(is_active=False)

    groups = paginate_queryset(queryset, page_size=20, page=request.GET.get("page", 1))

    stats = {
        "total": DonationGroup.objects.count(),
        "active": DonationGroup.objects.filter(is_active=True).count(),
        "inactive": DonationGroup.objects.filter(is_active=False).count(),
        "total_members_assigned": DonationGroupMembership.objects.values("member").distinct().count(),
    }

    return render(request, "settingsapp/donation_group_list.html", {
        "groups": groups,
        "stats": stats,
        "search_term": search_term,
        "status_filter": status_filter,
        "can_manage": request.user.has_admin_access() or request.user.has_executive_access(),
    })



@login_required
def donation_group_create(request):
    """Create a new donation group. Admin/Executive only."""
    if not (request.user.has_admin_access() or request.user.has_executive_access()):
        messages.error(request, "Admin or Executive access required.")
        return redirect("settingsapp:donation_group_list")

    if request.method == "POST":
        form = DonationGroupForm(request.POST)
        if form.is_valid():
            group = form.save(commit=False)
            group.created_by = request.user
            group.save()
            log_request_action(
                request, action="CREATE", object_type="DonationGroup",
                object_id=group.id, description=f"Created donation group '{group.name}'"
            )
            messages.success(request, f"Donation group '{group.name}' created successfully.")
            return redirect("settingsapp:donation_group_detail", pk=group.pk)
        else:
            for error_list in form.errors.values():
                for error in error_list:
                    messages.error(request, error)
    else:
        form = DonationGroupForm()

    return render(request, "settingsapp/donation_group_form.html", {
        "form": form,
        "action": "Create Donation Group",
    })


@login_required
def donation_group_update(request, pk):
    """Edit an existing donation group. Admin/Executive only."""
    if not (request.user.has_admin_access() or request.user.has_executive_access()):
        messages.error(request, "Admin or Executive access required.")
        return redirect("settingsapp:donation_group_list")

    group = get_object_or_404(DonationGroup, pk=pk)

    if request.method == "POST":
        form = DonationGroupForm(request.POST, instance=group)
        if form.is_valid():
            form.save()
            log_request_action(
                request, action="UPDATE", object_type="DonationGroup",
                object_id=group.id, description=f"Updated donation group '{group.name}'"
            )
            messages.success(request, f"Donation group '{group.name}' updated successfully.")
            return redirect("settingsapp:donation_group_detail", pk=group.pk)
        else:
            for error_list in form.errors.values():
                for error in error_list:
                    messages.error(request, error)
    else:
        form = DonationGroupForm(instance=group)

    return render(request, "settingsapp/donation_group_form.html", {
        "form": form,
        "group": group,
        "action": "Edit Donation Group",
    })


@login_required
def donation_group_delete(request, pk):
    """Delete a donation group. Admin only."""
    if not request.user.has_admin_access():
        messages.error(request, "Admin access required.")
        return redirect("settingsapp:donation_group_list")

    group = get_object_or_404(DonationGroup, pk=pk)

    if request.method == "POST":
        name = group.name
        group_id = group.id
        group.delete()
        log_request_action(
            request, action="DELETE", object_type="DonationGroup",
            object_id=group_id, description=f"Deleted donation group '{name}'"
        )
        messages.success(request, f"Donation group '{name}' deleted.")
        return redirect("settingsapp:donation_group_list")

    return render(request, "settingsapp/donation_group_confirm_delete.html", {"group": group})


@login_required
@require_POST
def donation_group_toggle_active(request, pk):
    """Activate/deactivate a donation group. Admin/Executive only."""
    if not (request.user.has_admin_access() or request.user.has_executive_access()):
        messages.error(request, "Admin or Executive access required.")
        return redirect("settingsapp:donation_group_list")

    group = get_object_or_404(DonationGroup, pk=pk)
    group.is_active = not group.is_active
    group.save(update_fields=["is_active", "updated_at"])

    log_request_action(
        request, action="UPDATE", object_type="DonationGroup",
        object_id=group.id,
        description=f"{'Activated' if group.is_active else 'Deactivated'} donation group '{group.name}'"
    )
    messages.success(
        request,
        f"'{group.name}' is now {'active' if group.is_active else 'inactive'}."
    )
    return redirect("settingsapp:donation_group_list")


@login_required
def donation_group_detail(request, pk):
    """
    View a donation group: report totals, member list, and donation history.
    
    Visible to ALL authenticated users. Management actions restricted
    to Admin/Executive via the can_manage flag in the template.
    """
    group = get_object_or_404(DonationGroup, pk=pk)

    memberships = group.memberships.select_related(
        "member", "member__umu_nna_clan", "added_by"
    ).order_by("member__full_name")

    member_search = request.GET.get("member_search", "")
    if member_search:
        memberships = memberships.filter(
            Q(member__full_name__icontains=member_search) |
            Q(member__serial_number__icontains=member_search) |
            Q(member__phone__icontains=member_search)
        )
    memberships_page = paginate_queryset(memberships, page_size=15, page=request.GET.get("mpage", 1))

    donations = group.confirmed_donations_queryset().select_related(
        "project", "member"
    ).order_by("-donation_date")[:100]

    assign_form = DonationGroupMemberAssignForm(group=group)

    can_manage = request.user.has_admin_access() or request.user.has_executive_access()

    return render(request, "settingsapp/donation_group_detail.html", {
        "group": group,
        "memberships": memberships_page,
        "donations": donations,
        "assign_form": assign_form,
        "member_search": member_search,
        "can_manage": can_manage,
        "report": {
            "total_members": group.member_count,
            "total_money_donated": group.total_money_donated,
            "total_projects_participated": group.total_projects_participated,
            "total_outstanding_pledges": group.total_outstanding_pledges,
        },
    })


@login_required
@require_POST
def donation_group_member_add(request, pk):
    """Assign a member to a donation group via the shared autocomplete search."""
    if not (request.user.has_admin_access() or request.user.has_executive_access()):
        messages.error(request, "Admin or Executive access required.")
        return redirect("settingsapp:donation_group_list")

    group = get_object_or_404(DonationGroup, pk=pk)
    form = DonationGroupMemberAssignForm(request.POST, group=group)

    if form.is_valid():
        member = form.cleaned_data["member"]
        DonationGroupMembership.objects.create(
            group=group, member=member, added_by=request.user
        )
        log_request_action(
            request, action="CREATE", object_type="DonationGroupMembership",
            object_id=group.id,
            description=f"Added {member.full_name} to donation group '{group.name}'"
        )
        messages.success(request, f"{member.full_name} added to '{group.name}'.")
    else:
        for error_list in form.errors.values():
            for error in error_list:
                messages.error(request, error)

    return redirect("settingsapp:donation_group_detail", pk=group.pk)


@login_required
@require_POST
def donation_group_member_remove(request, pk, membership_pk):
    """Remove a member from a donation group."""
    if not (request.user.has_admin_access() or request.user.has_executive_access()):
        messages.error(request, "Admin or Executive access required.")
        return redirect("settingsapp:donation_group_list")

    group = get_object_or_404(DonationGroup, pk=pk)
    membership = get_object_or_404(DonationGroupMembership, pk=membership_pk, group=group)
    member_name = membership.member.full_name
    membership.delete()

    log_request_action(
        request, action="DELETE", object_type="DonationGroupMembership",
        object_id=group.id,
        description=f"Removed {member_name} from donation group '{group.name}'"
    )
    messages.success(request, f"{member_name} removed from '{group.name}'.")
    return redirect("settingsapp:donation_group_detail", pk=group.pk)
