"""
Dashboard services for OYA KPIs and aggregations.
"""
import logging
from datetime import datetime
from django.db.models import Sum, Count, Q, Value, DecimalField
from django.db.models.functions import Coalesce
from django.core.cache import cache
from members.models import Member, Clan
from executives.models import Executive
from finance.models import Income, Expense, DuesPayment
from projects.models import Project
from operations.models import TaskForceMember, Motorcycle, CaseFile
from elections.models import Election
from notifications.models import Notification
from project_donations.models import Donation as ProjectDonation, OutsideDonor, Pledge
from settingsapp.models import DonationGroup, DonationGroupMembership

logger = logging.getLogger("oya")

CACHE_TIMEOUT = 300  # 5 minutes


def get_dashboard_kpis():
    """Get all dashboard KPIs with caching."""
    cache_key = "oya_dashboard_kpis"
    cached = cache.get(cache_key)
    if cached:
        return cached

    kpis = {
        "total_active_members": _get_total_active_members(),
        "treasury_balance": _get_treasury_balance(),
        "total_income": _get_total_income(),
        "total_expenses": _get_total_expenses(),
        "pending_cases": _get_pending_cases(),
        "active_task_force": _get_active_task_force_count(),
        "motorcycles_active": _get_motorcycles_active(),
        "projects_finished": _get_projects_finished(),
        "projects_at_hand": _get_projects_at_hand(),
        "projects_future": _get_projects_future(),
        "current_executives": _get_current_executives_count(),
        "upcoming_elections": _get_upcoming_elections(),
    }

    cache.set(cache_key, kpis, CACHE_TIMEOUT)
    return kpis


def get_member_statistics():
    """Get member statistics by clan and status."""
    cache_key = "oya_member_statistics"
    cached = cache.get(cache_key)
    if cached:
        return cached

    stats = {
        "by_clan": list(
            Clan.objects.annotate(
                member_count=Count("members")
            ).values("name", "member_count")
        ),
        "by_status": {
            "active": Member.objects.filter(status="ACTIVE").count(),
            "past": Member.objects.filter(status="PAST_MEMBER").count(),
            "removed": Member.objects.filter(status="REMOVED").count(),
        },
        "total": Member.objects.count(),
    }

    cache.set(cache_key, stats, CACHE_TIMEOUT)
    return stats


def get_finance_statistics():
    """Get finance statistics."""
    cache_key = "oya_finance_statistics"
    cached = cache.get(cache_key)
    if cached:
        return cached

    stats = {
        "total_income": _get_total_income(),
        "total_expenses": _get_total_expenses(),
        "treasury_balance": _get_treasury_balance(),
        "expenses_by_category": list(
            Expense.objects.values("category").annotate(
                total=Sum("amount")
            ).order_by("-total")
        ),
    }

    cache.set(cache_key, stats, CACHE_TIMEOUT)
    return stats


def get_income_expense_trend(year=None):
    """
    Get monthly income vs expenses data for chart display.
    
    If year is provided, filters to that year.
    If year is None, auto-detects the year with the most financial data
    (or uses current year if no historical data exists).
    This ensures existing records always show.
    """
    from django.db.models import Max, Min
    
    # Auto-detect year if not specified
    if year is None:
        # Find the latest year that has any income or expense records
        latest_income_year = Income.objects.aggregate(
            latest=Max('created_at__year')
        )['latest']
        latest_expense_year = Expense.objects.aggregate(
            latest=Max('created_at__year')
        )['latest']
        
        # Use the latest year that has data, or fall back to current year
        if latest_income_year or latest_expense_year:
            year = max(
                y for y in [latest_income_year, latest_expense_year] if y
            )
        else:
            year = datetime.now().year

    cache_key = f"oya_income_expense_trend_{year}"
    cached = cache.get(cache_key)
    if cached:
        return cached

    months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
              "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

    income_data = []
    expense_data = []

    for month in range(1, 13):
        # Income for this month and year
        monthly_income = Income.objects.filter(
            created_at__year=year,
            created_at__month=month
        ).aggregate(total=Sum("amount"))["total"] or 0

        # Expenses for this month and year
        monthly_expense = Expense.objects.filter(
            created_at__year=year,
            created_at__month=month
        ).aggregate(total=Sum("amount"))["total"] or 0

        income_data.append(float(monthly_income))
        expense_data.append(float(monthly_expense))

    # Determine which months to display
    current_year = datetime.now().year
    current_month = datetime.now().month

    if year == current_year:
        # Current year: only show up to current month
        display_months = months[:current_month]
        display_income = income_data[:current_month]
        display_expense = expense_data[:current_month]
    else:
        # Past year: show all 12 months
        display_months = months
        display_income = income_data
        display_expense = expense_data

    result = {
        "year": year,
        "months": display_months,
        "income": display_income,
        "expenses": display_expense,
        "total_income_ytd": sum(display_income),
        "total_expenses_ytd": sum(display_expense),
        "net_ytd": sum(display_income) - sum(display_expense),
    }

    cache.set(cache_key, result, CACHE_TIMEOUT)
    return result


def get_recent_activities(limit=10):
    """Get recent audit log activities for ADMIN/EXECUTIVE dashboards."""
    from auditlogs.models import AuditLog
    return AuditLog.objects.select_related("user").all().order_by("-created_at")[:limit]


def get_member_recent_activities(limit=10):
    """
    Get recent activities for FLOOR MEMBERS — restricted view.
    Only shows:
      - Money-related: income, expenses, dues payments recorded
      - Member additions: new members added
      - Member removals: members removed or status changed to PAST/REMOVED
    """
    from auditlogs.models import AuditLog
    from django.db.models import Q
    
    # Money-related keywords (case-insensitive search on action/description)
    money_keywords = [
        'income', 'expense', 'dues', 'payment', 'naira', 'recorded income',
        'recorded expense', 'finance', 'treasury', 'contribution', 'donation'
    ]
    
    # Member addition keywords
    add_keywords = [
        'added member', 'new member', 'member created', 'created member',
        'registered member', 'member added'
    ]
    
    # Member removal keywords
    remove_keywords = [
        'removed member', 'member removed', 'past member', 'member past',
        'status changed to past', 'status changed to removed',
        'deactivated member', 'member deactivated'
    ]
    
    # Build Q object for money-related
    money_q = Q()
    for kw in money_keywords:
        money_q |= Q(action__icontains=kw) | Q(description__icontains=kw)
    
    # Build Q object for member additions
    add_q = Q()
    for kw in add_keywords:
        add_q |= Q(action__icontains=kw) | Q(description__icontains=kw)
    
    # Build Q object for member removals
    remove_q = Q()
    for kw in remove_keywords:
        remove_q |= Q(action__icontains=kw) | Q(description__icontains=kw)
    
    # Combine: money OR add OR remove
    combined_q = money_q | add_q | remove_q
    
    # Also filter by object_type for finance/members operations
    model_q = Q(
        object_type__in=['income', 'expense', 'duespayment', 'member', 'members']
    )
    
    final_q = combined_q | model_q
    
    return AuditLog.objects.select_related("user").filter(
        final_q
    ).order_by("-created_at")[:limit]


def get_clan_distribution():
    """Get clan distribution data for charts."""
    cache_key = "oya_clan_distribution"
    cached = cache.get(cache_key)
    if cached:
        return cached

    clans = Clan.objects.annotate(
        member_count=Count("members")
    ).filter(member_count__gt=0).order_by("-member_count")

    data = {
        "labels": [clan.name for clan in clans],
        "data": [clan.member_count for clan in clans],
        "total": sum(clan.member_count for clan in clans),
    }

    cache.set(cache_key, data, CACHE_TIMEOUT)
    return data


def get_urgent_cases(limit=5):
    """Get urgent/open cases for dashboard display."""
    return CaseFile.objects.filter(
        Q(status="OPEN") | Q(status="IN_PROGRESS")
    ).select_related("respondent", "created_by").order_by("-created_at")[:limit]


def get_current_executives(limit=10):
    """Get current executives for directory."""
    try:
        return Executive.objects.filter(
            is_current=True
        ).select_related("member").order_by("post_order", "-created_at")[:limit]
    except Exception:
        return []


def get_active_task_force(limit=10):
    """Get active task force members for directory."""
    try:
        return TaskForceMember.objects.filter(
            is_active=True
        ).select_related("member").order_by("-assigned_date")[:limit]
    except Exception:
        return []


def get_recent_notices(limit=5):
    """Get recent notifications/notices."""
    try:
        return Notification.objects.filter(
            is_active=True
        ).order_by("-created_at")[:limit]
    except Exception:
        return []


def get_member_contributions(member):
    """Get contribution history for a specific member."""
    from finance.models import Income
    try:
        contributions = Income.objects.filter(
            paid_by__icontains=member.full_name
        ).order_by("-created_at")[:6]
        total = Income.objects.filter(
            paid_by__icontains=member.full_name
        ).aggregate(total=Sum("amount"))["total"] or 0
        return {
            "contributions": contributions,
            "total_contributed": total,
        }
    except Exception:
        return {
            "contributions": [],
            "total_contributed": 0,
        }


def invalidate_dashboard_cache():
    """Invalidate all dashboard cache keys."""
    cache.delete("oya_dashboard_kpis")
    cache.delete("oya_member_statistics")
    cache.delete("oya_finance_statistics")
    cache.delete("oya_clan_distribution")
    cache.delete("oya_dashboard_extras")
    # Also invalidate trend cache for current and nearby years
    current_year = datetime.now().year
    for y in range(current_year - 2, current_year + 2):
        cache.delete(f"oya_income_expense_trend_{y}")


def get_dashboard_extras():
    """Cache the remaining per-request dashboard queries (recent activity, notices, etc.)."""
    cache_key = "oya_dashboard_extras"
    cached = cache.get(cache_key)
    if cached:
        return cached

    extras = {
        "recent_activities": list(get_recent_activities()),
        "member_recent_activities": list(get_member_recent_activities()),
        "urgent_cases": list(get_urgent_cases()),
        "executives": list(get_current_executives()),
        "task_force": list(get_active_task_force()),
        "notices": list(get_recent_notices()),
        "active_fundraising_projects": Project.objects.filter(
            enable_fundraising=True, fundraising_status="ACTIVE"
        ).count(),
        "total_outside_donors": OutsideDonor.objects.count(),
        "total_raised_through_invitees": ProjectDonation.objects.filter(
            status="CONFIRMED", invited_by__isnull=False
        ).aggregate(
            total=Coalesce(Sum("amount"), Value(0, output_field=DecimalField()))
        )["total"],
        # ─── Feature 14: Donation Groups, donation types, pledges, dues ───
        "total_donation_groups": _get_total_donation_groups(),
        "members_in_donation_groups": _get_members_in_donation_groups(),
        "total_money_donations": _get_total_money_donations(),
        "total_material_donations": _get_total_material_donations(),
        "total_labour_contributions": _get_total_labour_contributions(),
        "pending_pledges": _get_pending_pledges_count(),
        "completed_pledges": _get_completed_pledges_count(),
        "outstanding_pledge_amount": _get_outstanding_pledge_amount(),
        "yearly_dues_debtors": _get_yearly_dues_debtors_count(),
        "outstanding_dues": _get_outstanding_dues_amount(),
    }
    cache.set(cache_key, extras, CACHE_TIMEOUT)
    return extras


# --- Private helper functions ---

def _get_total_active_members():
    """Get total number of active members."""
    try:
        return Member.objects.filter(status="ACTIVE").count()
    except Exception:
        return 0


def _get_treasury_balance():
    """Calculate treasury balance (total income - total expenses)."""
    try:
        total_income = Income.objects.aggregate(total=Sum("amount"))["total"] or 0
        total_expenses = Expense.objects.aggregate(total=Sum("amount"))["total"] or 0
        return total_income - total_expenses
    except Exception:
        return 0


def _get_total_income():
    """Get total income."""
    try:
        return Income.objects.aggregate(total=Sum("amount"))["total"] or 0
    except Exception:
        return 0


def _get_total_expenses():
    """Get total expenses."""
    try:
        return Expense.objects.aggregate(total=Sum("amount"))["total"] or 0
    except Exception:
        return 0


def _get_pending_cases():
    """Get count of open and in-progress cases."""
    try:
        return CaseFile.objects.filter(
            Q(status="OPEN") | Q(status="IN_PROGRESS")
        ).count()
    except Exception:
        return 0


def _get_active_task_force_count():
    """Get count of active task force members."""
    try:
        return TaskForceMember.objects.filter(is_active=True).count()
    except Exception:
        return 0


def _get_motorcycles_active():
    """Get count of motorcycles that are not grounded."""
    try:
        return Motorcycle.objects.exclude(condition="GROUNDED").count()
    except Exception:
        return 0


def _get_projects_finished():
    """Get count of finished projects."""
    try:
        return Project.objects.filter(status="FINISHED").count()
    except Exception:
        return 0


def _get_projects_at_hand():
    """Get count of ongoing projects."""
    try:
        return Project.objects.filter(status="AT_HAND").count()
    except Exception:
        return 0


def _get_projects_future():
    """Get count of future projects."""
    try:
        return Project.objects.filter(status="FUTURE").count()
    except Exception:
        return 0


def _get_current_executives_count():
    """Get count of current executives."""
    try:
        return Executive.objects.filter(is_current=True).count()
    except Exception:
        return 0


def _get_upcoming_elections():
    """Get count of upcoming elections."""
    try:
        return Election.objects.filter(status__in=["UPCOMING", "ONGOING"]).count()
    except Exception:
        return 0

def _get_total_donation_groups():
    """Get count of active donation groups (Feature 14)."""
    try:
        return DonationGroup.objects.filter(is_active=True).count()
    except Exception:
        return 0


def _get_members_in_donation_groups():
    """Get count of distinct members assigned to at least one donation group (Feature 14)."""
    try:
        return DonationGroupMembership.objects.values("member").distinct().count()
    except Exception:
        return 0


def _get_total_money_donations():
    """Get total confirmed Money donations across all projects (Feature 14)."""
    try:
        return ProjectDonation.objects.filter(
            status="CONFIRMED", donation_type="MONEY"
        ).aggregate(
            total=Coalesce(Sum("amount"), Value(0, output_field=DecimalField()))
        )["total"]
    except Exception:
        return 0


def _get_total_material_donations():
    """Get count of confirmed Material donations (Feature 14)."""
    try:
        return ProjectDonation.objects.filter(
            status="CONFIRMED", donation_type="MATERIAL"
        ).count()
    except Exception:
        return 0


def _get_total_labour_contributions():
    """Get count of confirmed Labour contributions (Feature 14)."""
    try:
        return ProjectDonation.objects.filter(
            status="CONFIRMED", donation_type="LABOUR"
        ).count()
    except Exception:
        return 0


def _get_pending_pledges_count():
    """Get count of pending + partially paid pledges (Feature 14)."""
    try:
        return Pledge.objects.filter(status__in=["PENDING", "PARTIALLY_PAID"]).count()
    except Exception:
        return 0


def _get_completed_pledges_count():
    """Get count of completed pledges (Feature 14)."""
    try:
        return Pledge.objects.filter(status="COMPLETED").count()
    except Exception:
        return 0


def _get_outstanding_pledge_amount():
    """Get total outstanding balance across active pledges (Feature 14)."""
    try:
        active = Pledge.objects.exclude(status__in=["COMPLETED", "CANCELLED"])
        return sum((p.outstanding_balance for p in active), 0)
    except Exception:
        return 0


def _get_yearly_dues_debtors_count():
    """Get count of distinct members with any outstanding yearly dues (Feature 14)."""
    try:
        from accounts.models import User
        from core.utils import exclude_admin_users
        current_year = datetime.now().year

        members = list(
            exclude_admin_users(
                User.objects.filter(serial_number__isnull=False).exclude(serial_number="")
            )
        )
        # One query for all fully-paid (member, year) pairs instead of N queries.
        paid_pairs = set(
            DuesPayment.objects.filter(
                member__in=members, amount_paid__gte=DuesPayment.YEARLY_DUES_AMOUNT
            ).values_list("member_id", "year")
        )

        debtor_count = 0
        for member in members:
            join_year = DuesPayment.get_member_join_year(member)
            start_year = max(join_year, 2020)
            if start_year > current_year:
                continue
            owed_years = set(range(start_year, current_year + 1))
            paid_years = {year for (mid, year) in paid_pairs if mid == member.id}
            if owed_years - paid_years:
                debtor_count += 1
        return debtor_count
    except Exception:
        return 0


def _get_outstanding_dues_amount():
    """Get total outstanding yearly dues amount across all active members (Feature 14)."""
    try:
        from accounts.models import User
        from core.utils import exclude_admin_users
        current_year = datetime.now().year

        members = list(
            exclude_admin_users(
                User.objects.filter(serial_number__isnull=False).exclude(serial_number="")
            )
        )
        # One query for total paid per member instead of N queries.
        paid_by_member = {
            row["member_id"]: row["total"]
            for row in DuesPayment.objects.filter(
                member__in=members, year__lte=current_year
            ).values("member_id").annotate(
                total=Coalesce(Sum("amount_paid"), Value(0, output_field=DecimalField()))
            )
        }

        total_outstanding = 0
        for member in members:
            join_year = DuesPayment.get_member_join_year(member)
            start_year = max(join_year, 2020)
            expected_years = current_year - start_year + 1
            if expected_years <= 0:
                continue
            total_expected = expected_years * DuesPayment.YEARLY_DUES_AMOUNT
            total_paid = paid_by_member.get(member.id, 0)
            total_outstanding += max(total_expected - total_paid, 0)
        return total_outstanding
    except Exception:
        return 0
