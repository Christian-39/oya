"""
Views for OYA dashboard.
"""
import logging
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.urls import reverse
from django.http import JsonResponse
from django.db.models import Q
from django.utils import timezone
from members.models import Member
from accounts.models import User
from projects.models import Project
from operations.models import CaseFile, TaskForceMember, Motorcycle
from project_donations.models import Donation as ProjectDonation, OutsideDonor
from finance.models import Income, DuesPayment
from django.db.models import Sum, Value, DecimalField
from django.db.models.functions import Coalesce

from .services import (
    get_dashboard_kpis,
    get_member_statistics,
    get_finance_statistics,
    get_dashboard_extras,
    get_recent_activities,
    get_clan_distribution,
    get_urgent_cases,
    get_current_executives,
    get_active_task_force,
    get_recent_notices,
    get_member_contributions,
    get_income_expense_trend,
    invalidate_dashboard_cache,
)

logger = logging.getLogger("oya")

YEARLY_DUES = 5000


@login_required
def global_search_ajax(request):
    """AJAX endpoint for topbar global search."""
    query = request.GET.get("q", "").strip()
    if len(query) < 2:
        return JsonResponse({"results": [], "view_all_url": None})

    results = []
    q = query

    # ─── Members ───
    for m in Member.objects.filter(
        Q(full_name__icontains=q)
        | Q(serial_number__icontains=q)
        | Q(phone__icontains=q)
        | Q(state_or_abroad__icontains=q)
    )[:5]:
        try:
            url = reverse("members:member_detail", kwargs={"pk": m.pk})
        except NoReverseMatch:
            url = "#"
        results.append({
            "type": "member",
            "name": f"{m.full_name} ({m.serial_number})",
            "url": url,
        })

    # ─── Users ───
    for u in User.objects.filter(
        Q(full_name__icontains=q)
        | Q(serial_number__icontains=q)
        | Q(phone__icontains=q)
    )[:5]:
        try:
            url = reverse("accounts:profile")
        except NoReverseMatch:
            url = "#"
        results.append({
            "type": "user",
            "name": u.full_name or u.serial_number,
            "url": url,
        })

    # ─── Case Files ───
    for c in CaseFile.objects.filter(
        Q(title__icontains=q)
        | Q(case_number__icontains=q)
        | Q(respondent__full_name__icontains=q)
    )[:5]:
        try:
            url = reverse("operations:case_detail", kwargs={"pk": c.pk})
        except NoReverseMatch:
            url = "#"
        results.append({
            "type": "case",
            "name": f"{c.case_number or 'Case'}: {c.title}",
            "url": url,
        })

    # ─── Projects ───
    try:
        from projects.models import Project
        for p in Project.objects.filter(
            Q(title__icontains=q) | Q(description__icontains=q)
        )[:5]:
            try:
                url = reverse("projects:project_detail", kwargs={"pk": p.pk})
            except NoReverseMatch:
                url = "#"
            results.append({
                "type": "project",
                "name": p.title,
                "url": url,
            })
    except Exception:
        pass

    # ─── Outside Donors ───
    try:
        from project_donations.models import OutsideDonor
        for d in OutsideDonor.objects.filter(
            Q(full_name__icontains=q) | Q(phone_number__icontains=q)
        )[:5]:
            try:
                url = reverse("project_donations:outside_donor_detail", kwargs={"pk": d.pk})
            except NoReverseMatch:
                url = "#"
            results.append({
                "type": "member",
                "name": f"{d.full_name} (Outside Donor)",
                "url": url,
            })
    except Exception:
        pass

    return JsonResponse({
        "results": results,
        "view_all_url": None,
    })


@login_required
def financial_trend_ajax(request):
    """AJAX endpoint to return income vs expenses trend data as JSON."""
    from datetime import datetime
    year_param = request.GET.get("year")
    try:
        year = int(year_param) if year_param else None  # None = auto-detect
    except ValueError:
        year = None

    trend_data = get_income_expense_trend(year=year)
    return JsonResponse(trend_data)


def _patch_finance_stats_with_project_donations(finance_stats):
    """Helper: merge confirmed project donations into finance stats dict.

    get_finance_statistics() may already include auto-created PROJECT_DONATION
    Income records (from signals). We subtract those first, then add the
    authoritative ProjectDonation total so project donations are counted
    exactly once — never doubled.
    """
    total_project_donations = ProjectDonation.objects.filter(
        status="CONFIRMED"
    ).aggregate(
        total=Coalesce(Sum("amount"), Value(0, output_field=DecimalField()))
    )["total"] or Decimal("0")

    # Auto-created Income records for project donations (managed by signals).
    # These may already be included in get_finance_statistics() totals.
    project_donation_income = Income.objects.filter(
        income_type="PROJECT_DONATION"
    ).aggregate(
        total=Coalesce(Sum("amount"), Value(0, output_field=DecimalField()))
    )["total"] or Decimal("0")

    if isinstance(finance_stats, dict):
        finance_stats["total_project_donations"] = total_project_donations
        if "total_income" in finance_stats:
            finance_stats["total_income"] = (
                finance_stats["total_income"] - project_donation_income + total_project_donations
            )
        if "treasury_balance" in finance_stats:
            finance_stats["treasury_balance"] = (
                finance_stats["treasury_balance"] - project_donation_income + total_project_donations
            )

    return finance_stats, total_project_donations


def _patch_finance_stats_with_prepaid_dues(finance_stats):
    """Helper: add prepaid dues (future years fully paid) to finance stats.

    Prepaid dues represent cash already received, so they must be included
    in total dues collected, total income, and treasury balance.
    """
    current_year = timezone.now().year
    total_prepaid = DuesPayment.objects.filter(
        year__gt=current_year,
        amount_paid__gte=YEARLY_DUES,
    ).aggregate(
        total=Coalesce(Sum("amount_paid"), Value(0, output_field=DecimalField()))
    )["total"] or Decimal("0")

    if isinstance(finance_stats, dict):
        finance_stats["total_prepaid"] = total_prepaid
        if "total_dues" in finance_stats:
            finance_stats["total_dues"] = finance_stats["total_dues"] + total_prepaid
        if "total_income" in finance_stats:
            finance_stats["total_income"] = finance_stats["total_income"] + total_prepaid
        if "treasury_balance" in finance_stats:
            finance_stats["treasury_balance"] = finance_stats["treasury_balance"] + total_prepaid

    return finance_stats, total_prepaid


@login_required
def index(request):
    """Main admin/executive dashboard view with all KPIs."""
    kpis = get_dashboard_kpis()
    member_stats = get_member_statistics()
    finance_stats = get_finance_statistics()

    # Merge confirmed project donations into dashboard finance stats
    finance_stats, total_project_donations = _patch_finance_stats_with_project_donations(finance_stats)

    # Merge prepaid dues into dashboard finance stats (cash already received)
    finance_stats, total_prepaid = _patch_finance_stats_with_prepaid_dues(finance_stats)

    # Sync patched finance stats back into kpis so templates using kpis.treasury_balance are correct
    if isinstance(finance_stats, dict):
        tb = finance_stats.get("treasury_balance", 0)
        ti = finance_stats.get("total_income", 0)
        if isinstance(kpis, dict):
            kpis["treasury_balance"] = tb
            kpis["total_income"] = ti
        else:
            setattr(kpis, "treasury_balance", tb)
            setattr(kpis, "total_income", ti)

    # Expose as top-level context variables (for templates that use them directly)
    total_income = finance_stats.get("total_income", 0) if isinstance(finance_stats, dict) else 0
    treasury_balance = finance_stats.get("treasury_balance", 0) if isinstance(finance_stats, dict) else 0
    total_expenses = finance_stats.get("total_expenses", 0) if isinstance(finance_stats, dict) else 0

    # Cached extras: recent activities, urgent cases, executives, task force,
    # notices, fundraising stats — all from one cache hit instead of ~8 queries.
    extras = get_dashboard_extras()

    # Real data for dashboard components
    clan_distribution = get_clan_distribution()

    # Financial trend data for charts - auto-detects year with data
    trend_data = get_income_expense_trend()

    # Role-based context
    is_admin = request.user.has_admin_access()
    is_executive = request.user.has_executive_access()

    context = {
        "kpis": kpis,
        "member_stats": member_stats,
        "finance_stats": finance_stats,
        "recent_activities": extras["recent_activities"],
        "clan_distribution": clan_distribution,
        "urgent_cases": extras["urgent_cases"],
        "executives": extras["executives"],
        "task_force": extras["task_force"],
        "notices": extras["notices"],
        "trend_data": trend_data,
        "is_admin": is_admin,
        "is_executive": is_executive,
        # Top-level finance variables for templates
        "total_income": total_income,
        "treasury_balance": treasury_balance,
        "total_expenses": total_expenses,
        # Project donations
        "total_project_donations": total_project_donations,
        "active_fundraising_projects": extras["active_fundraising_projects"],
        "total_outside_donors": extras["total_outside_donors"],
        "total_raised_through_invitees": extras["total_raised_through_invitees"],
        # Prepaid dues
        "total_prepaid": total_prepaid,
        # Feature 14: Donation Groups, donation types, pledges, dues
        "total_donation_groups": extras["total_donation_groups"],
        "members_in_donation_groups": extras["members_in_donation_groups"],
        "total_money_donations": extras["total_money_donations"],
        "total_material_donations": extras["total_material_donations"],
        "total_labour_contributions": extras["total_labour_contributions"],
        "pending_pledges": extras["pending_pledges"],
        "completed_pledges": extras["completed_pledges"],
        "outstanding_pledge_amount": extras["outstanding_pledge_amount"],
        "yearly_dues_debtors": extras["yearly_dues_debtors"],
        "outstanding_dues": extras["outstanding_dues"],
    }
    return render(request, "dashboard/admin_dashboard.html", context)


@login_required
def member_dashboard(request):
    """Member-only dashboard view."""
    kpis = get_dashboard_kpis()
    member_stats = get_member_statistics()
    finance_stats = get_finance_statistics()

    # Merge confirmed project donations into dashboard finance stats
    finance_stats, total_project_donations = _patch_finance_stats_with_project_donations(finance_stats)

    # Merge prepaid dues into dashboard finance stats (cash already received)
    finance_stats, total_prepaid = _patch_finance_stats_with_prepaid_dues(finance_stats)

    # Sync patched finance stats back into kpis so templates using kpis.treasury_balance are correct
    if isinstance(finance_stats, dict):
        tb = finance_stats.get("treasury_balance", 0)
        ti = finance_stats.get("total_income", 0)
        if isinstance(kpis, dict):
            kpis["treasury_balance"] = tb
            kpis["total_income"] = ti
        else:
            setattr(kpis, "treasury_balance", tb)
            setattr(kpis, "total_income", ti)

    # Top-level finance variables for templates
    total_income = finance_stats.get("total_income", 0) if isinstance(finance_stats, dict) else 0
    treasury_balance = finance_stats.get("treasury_balance", 0) if isinstance(finance_stats, dict) else 0

    # Floor members get restricted activities (money + member add/remove only)
    member_activities = get_member_recent_activities(limit=5)

    # Cached extras for shared dashboard data
    extras = get_dashboard_extras()

    # Real data for member dashboard
    clan_distribution = get_clan_distribution()

    # Financial trend data for charts
    trend_data = get_income_expense_trend()

    # Get member-specific contribution data
    try:
        from members.models import Member
        member = Member.objects.get(user=request.user)
        contribution_data = get_member_contributions(member)
        contributions = contribution_data["contributions"]
        total_contributed = contribution_data["total_contributed"]
    except (Member.DoesNotExist, Exception):
        member = None
        contributions = []
        total_contributed = 0

    context = {
        "kpis": kpis,
        "member_stats": member_stats,
        "finance_stats": finance_stats,
        "total_income": total_income,
        "treasury_balance": treasury_balance,
        "total_project_donations": total_project_donations,
        "active_fundraising_projects": extras["active_fundraising_projects"],
        "total_outside_donors": extras["total_outside_donors"],
        "total_raised_through_invitees": extras["total_raised_through_invitees"],
        "recent_activities": member_activities,  # restricted view for members
        "clan_distribution": clan_distribution,
        "executives": extras["executives"],
        "task_force": extras["task_force"],
        "notices": extras["notices"],
        "member": member,
        "contributions": contributions,
        "total_contributed": total_contributed,
        "trend_data": trend_data,
        "is_member": True,
        "total_prepaid": total_prepaid,
    }
    return render(request, "dashboard/member_dashboard.html", context)


@login_required
def admin_dashboard(request):
    """Admin-only dashboard view (redirects to main index with admin context)."""
    if not request.user.has_admin_access():
        messages.error(request, "Admin access required.")
        return render(request, "dashboard/member_dashboard.html")

    return index(request)