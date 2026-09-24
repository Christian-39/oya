"""
Views for OYA members.
"""
import logging
from decimal import Decimal
from dashboard.services import invalidate_dashboard_cache
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q, Count
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from auditlogs.services import log_action
from accounts.permissions import AdminRequiredMixin, ExecutiveRequiredMixin
from core.utils import paginate_queryset, build_search_query, exclude_admin_members
from .models import Member, Clan
from .forms import MemberForm, MemberUpdateForm, MemberRemoveForm, ClanForm

logger = logging.getLogger("oya")


@login_required
def member_list(request):
    """List all members with search, filter, and pagination."""
    queryset = Member.objects.select_related("umu_nna_clan").prefetch_related(
        "executive_roles",
        "task_force_assignments",
    ).all()

    search_term = request.GET.get("search", "")
    if search_term:
        search_fields = [
            "serial_number", "full_name", "phone",
            "state_or_abroad", "umu_nna_clan__name"
        ]
        queryset = queryset.filter(build_search_query(search_fields, search_term))

    status_filter = request.GET.get("status", "")
    if status_filter:
        queryset = queryset.filter(status=status_filter)

    clan_filter = request.GET.get("clan", "")
    if clan_filter:
        queryset = queryset.filter(umu_nna_clan_id=clan_filter)

    order_by = request.GET.get("order_by", "-created_at")
    queryset = queryset.order_by(order_by)

    paginator = Paginator(queryset, 25)
    page = request.GET.get("page", 1)
    members = paginator.get_page(page)

    stats = Member.objects.aggregate(
        total=Count("id"),
        active=Count("id", filter=Q(status="ACTIVE")),
        past=Count("id", filter=Q(status="PAST_MEMBER")),
        removed=Count("id", filter=Q(status="REMOVED")),
    )

    return render(request, "members/member_list.html", {
        "members": members,
        "clans": Clan.objects.all(),
        "stats": stats,
        "search_term": search_term,
        "status_filter": status_filter,
        "clan_filter": clan_filter,
        "status_choices": Member.STATUS_CHOICES,
    })


@login_required
def member_detail(request, pk):
    """Display member details with outside donors and donation data."""
    member = get_object_or_404(Member.objects.select_related("umu_nna_clan"), pk=pk)
    
    from project_donations.models import Donation, OutsideDonor, Pledge
    from django.db.models import Sum, Value, DecimalField
    from django.db.models.functions import Coalesce
    
    # Outside donors invited by this member
    outside_donors_invited = member.invited_outside_donors.select_related().all()
    total_invited_donors = outside_donors_invited.count()
    total_raised_through_invitees = outside_donors_invited.aggregate(
        total=Coalesce(Sum("donations__amount", filter=Q(donations__status="CONFIRMED")), Value(0, output_field=DecimalField()))
    )["total"] or 0
    
    # Personal project donations
    personal_donations = Donation.objects.filter(
        member=member, status="CONFIRMED"
    ).select_related("project").order_by("-donation_date")
    total_personal_donations = personal_donations.aggregate(
        total=Coalesce(Sum("amount"), Value(0, output_field=DecimalField()))
    )["total"] or 0
    projects_supported = personal_donations.values("project").distinct().count()

    # ─── Feature 13: donation type breakdown ───
    money_donations = personal_donations.filter(donation_type="MONEY")
    material_donations = personal_donations.filter(donation_type="MATERIAL")
    labour_contributions = personal_donations.filter(donation_type="LABOUR")

    # ─── Feature 13: donation groups ───
    donation_groups = member.donation_group_memberships.select_related("group").order_by("-date_added")

    # ─── Feature 13: pledges ───
    member_pledges = Pledge.objects.filter(member=member).select_related("project").order_by("-created_at")
    active_pledges = member_pledges.filter(status__in=["PENDING", "PARTIALLY_PAID"])
    completed_pledges = member_pledges.filter(status="COMPLETED")
    outstanding_pledge_total = sum(
        (p.outstanding_balance for p in active_pledges), Decimal("0")
    )
    
    return render(request, "members/member_detail.html", {
        "member": member,
        "outside_donors_invited": outside_donors_invited,
        "total_invited_donors": total_invited_donors,
        "total_raised_through_invitees": total_raised_through_invitees,
        "personal_donations": personal_donations,
        "total_personal_donations": total_personal_donations,
        "projects_supported": projects_supported,
        "money_donations": money_donations,
        "material_donations": material_donations,
        "labour_contributions": labour_contributions,
        "donation_groups": donation_groups,
        "active_pledges": active_pledges,
        "completed_pledges": completed_pledges,
        "outstanding_pledge_total": outstanding_pledge_total,
    })


@login_required
def member_create(request):
    """Create a new member with login account and PIN."""
    if not request.user.has_executive_access():
        messages.error(request, "Executive access required.")
        return redirect("members:member_list")

    generated_pin = None

    if request.method == "POST":
        form = MemberForm(request.POST, request.FILES)
        if form.is_valid():
            member = form.save()

            # Get generated PIN from the instance
            if hasattr(member, '_generated_pin'):
                generated_pin = member._generated_pin

            log_action(
                user=request.user,
                action="CREATE",
                object_type="Member",
                object_id=member.id,
                ip_address=getattr(request, "client_ip", ""),
                description=f"Created member {member.serial_number} with login account"
            )
            messages.success(request, f"Member {member.serial_number} created successfully.")
            invalidate_dashboard_cache()

            # Render form with PIN banner (don't redirect — admin needs to see PIN!)
            return render(request, "members/member_form.html", {
                "form": MemberForm(),
                "title": "Add New Member",
                "action": "Create",
                "generated_pin": generated_pin,
                "member": member,
            })
        else:
            # CRITICAL FIX: Properly iterate through nested error lists
            for field_name, error_list in form.errors.items():
                for error in error_list:
                    messages.error(request, f"{field_name}: {error}")
    else:
        form = MemberForm()

    return render(request, "members/member_form.html", {
        "form": form,
        "title": "Add New Member",
        "action": "Create",
        "generated_pin": generated_pin,
    })


@login_required
def member_update(request, pk):
    """Update an existing member and sync login account."""
    if not request.user.has_executive_access():
        messages.error(request, "Executive access required.")
        return redirect("members:member_list")

    member = get_object_or_404(Member, pk=pk)
    updated_pin = None

    if request.method == "POST":
        form = MemberUpdateForm(request.POST, request.FILES, instance=member)
        if form.is_valid():
            member = form.save()

            if hasattr(member, '_updated_pin'):
                updated_pin = member._updated_pin
            elif hasattr(member, '_generated_pin'):
                updated_pin = member._generated_pin

            log_action(
                user=request.user,
                action="UPDATE",
                object_type="Member",
                object_id=member.id,
                ip_address=getattr(request, "client_ip", ""),
                description=f"Updated member {member.serial_number}"
            )
            messages.success(request, f"Member {member.serial_number} updated successfully.")
            invalidate_dashboard_cache()

            # Render form with PIN banner
            return redirect("members:member_list")
        else:
            # CRITICAL FIX: Properly iterate through nested error lists
            for field_name, error_list in form.errors.items():
                for error in error_list:
                    messages.error(request, f"{field_name}: {error}")
    else:
        form = MemberUpdateForm(instance=member)

    return render(request, "members/member_form.html", {
        "form": form,
        "title": "Update Member",
        "action": "Update",
        "member": member,
        "updated_pin": updated_pin,
    })


@login_required
def member_remove(request, pk):
    """Remove a member with a reason."""
    if not request.user.has_executive_access():
        messages.error(request, "Executive access required.")
        return redirect("members:member_list")

    member = get_object_or_404(Member, pk=pk)

    if request.method == "POST":
        form = MemberRemoveForm(request.POST, instance=member)
        if form.is_valid():
            # Save reason/offense from form
            member = form.save(commit=False)

            # FORCE the status update directly in the DB
            member.status = "REMOVED"
            member.save(update_fields=["status", "removal_reason", "offense_committed", "updated_at"])

            # Deactivate linked User account
            try:
                from accounts.models import User
                user = User.objects.get(serial_number=member.serial_number)
                user.is_active = False
                user.save(update_fields=["is_active"])
            except User.DoesNotExist:
                pass

            log_action(
                user=request.user,
                action="UPDATE",
                object_type="Member",
                object_id=member.id,
                ip_address=getattr(request, "client_ip", ""),
                description=f"Removed member {member.serial_number}: {member.removal_reason}"
            )
            messages.success(request, f"Member {member.serial_number} has been removed.")
            invalidate_dashboard_cache()
            return redirect("members:member_list")
    else:
        form = MemberRemoveForm(instance=member)

    return render(request, "members/member_remove.html", {
        "form": form,
        "member": member
    })  

@login_required
def member_delete(request, pk):
    """Delete a member permanently (admin only)."""
    if not request.user.has_admin_access():
        messages.error(request, "Admin access required.")
        return redirect("members:member_list")

    member = get_object_or_404(Member, pk=pk)

    if request.method == "POST":
        serial = member.serial_number

        try:
            from accounts.models import User
            user = User.objects.get(serial_number=serial)
            user.delete()
        except User.DoesNotExist:
            pass

        member.delete()
        log_action(
            user=request.user,
            action="DELETE",
            object_type="Member",
            object_id=pk,
            ip_address=getattr(request, "client_ip", ""),
            description=f"Deleted member {serial}"
        )
        messages.success(request, f"Member {serial} deleted permanently.")
        invalidate_dashboard_cache()
        return redirect("members:member_list")

    return render(request, "members/member_confirm_delete.html", {"member": member})


@login_required
def clan_list(request):
    """List all clans with member counts."""
    clans = Clan.objects.annotate(member_count=Count("members")).all()
    return render(request, "members/clan_list.html", {"clans": clans})


@login_required
def clan_create(request):
    """Create a new clan - supports both regular and AJAX requests."""
    if not request.user.has_executive_access():
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'error': 'Executive access required.'}, status=403)
        messages.error(request, "Executive access required.")
        return redirect("members:clan_list")

    if request.method == "POST":
        form = ClanForm(request.POST)
        if form.is_valid():
            clan = form.save()
            log_action(
                user=request.user,
                action="CREATE",
                object_type="Clan",
                object_id=clan.id,
                ip_address=getattr(request, "client_ip", ""),
                description=f"Created clan {clan.name}"
            )

            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': True,
                    'id': clan.id,
                    'name': clan.name,
                    'member_count': 0
                })

            messages.success(request, f"Clan '{clan.name}' created successfully.")
            invalidate_dashboard_cache()
            return redirect("members:clan_list")
        else:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                errors = []
                for field_errors in form.errors.values():
                    errors.extend(field_errors)
                return JsonResponse({'success': False, 'error': ' '.join(errors)}, status=400)

            for field_name, error_list in form.errors.items():
                for error in error_list:
                    messages.error(request, f"{field_name}: {error}")
    else:
        form = ClanForm()

    return render(request, "members/clan_form.html", {
        "form": form,
        "title": "Add Clan",
        "action": "Create"
    })

@login_required
@require_http_methods(["GET"])
def member_autocomplete_search(request):
    q = request.GET.get("q", "").strip()
    if len(q) < 1:
        return JsonResponse({"results": []})

    status_filter = request.GET.get("status", "ACTIVE")
    members = Member.objects.select_related("umu_nna_clan")
    if status_filter:
        members = members.filter(status=status_filter)
    # Defense-in-depth: no matter what status filter (or lack of one) is
    # requested, a Removed member must never be selectable here — and
    # Admins never appear here either (they manage/monitor; they don't
    # get selected for donations, pledges, task force, etc.).
    members = members.exclude(status="REMOVED")
    members = exclude_admin_members(members)

    members = members.filter(
        Q(full_name__icontains=q) |
        Q(serial_number__icontains=q) |
        Q(phone__icontains=q)
    ).order_by("full_name")[:15]

    results = []
    for m in members:
        results.append({
            "id": m.id,
            "full_name": m.full_name,          # ← JS displays this
            "serial_number": m.serial_number,  # ← JS shows as subtitle
            "phone": m.phone,                  # ← JS shows as subtitle
            "role": m.status,
            "photo_url": m.photo.url if m.photo and hasattr(m.photo, "url") else ""
        })

    return JsonResponse({"results": results})


@login_required
def member_stats_ajax(request):
    """AJAX endpoint for member statistics."""
    stats = {
        "total": Member.objects.count(),
        "active": Member.objects.filter(status="ACTIVE").count(),
        "past": Member.objects.filter(status="PAST_MEMBER").count(),
        "removed": Member.objects.filter(status="REMOVED").count(),
        "by_clan": list(
            Clan.objects.annotate(
                count=Count("members")
            ).values("name", "count")
        ),
    }
    return JsonResponse(stats)