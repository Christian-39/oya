"""
Executive Handover Report engine.

An "Administration" is the cohort of Executives produced by a single
Election (grouped via Executive.elected_via). Executives that predate the
`elected_via` field (or were never tied to an election) are grouped together
under a synthetic "Founding Administration".

This module is intentionally the *only* place that knows how to assemble an
Executive Handover Report. Views should call `list_administrations()` and
`build_administration_report()` rather than querying models directly, so the
report logic stays in one place as new record types are added.

── Adding a new record type to every future handover report ──────────────
Call `register_handover_section(fn)` once (e.g. from any app's `apps.py`
`ready()` method) with a callable of the shape:

    def my_section(start, end, administration):
        return {
            "key": "my_section",
            "title": "My New Records",
            "description": "Optional helper text.",
            "type": "table",                 # "table" | "list" | "cards"
            "headers": ["Column A", "Column B"],   # only for type="table"
            "rows": [["value", "value"], ...],     # only for type="table"
            "items": [...],                         # for "list"/"cards"
            "count": 0,
        }

`start`/`end` are `date` objects bounding the administration's tenure
(`end` is `date.today()` for a still-serving/current administration).
Returning `None` omits the section for that report. Exceptions inside a
registered builder are caught and logged so one broken section never takes
down the whole report.
"""
import logging
from datetime import date
from decimal import Decimal

from django.db.models import Sum, Count
from django.utils import timezone

logger = logging.getLogger("oya")

FOUNDING_KEY = "founding"

_EXTRA_SECTION_BUILDERS = []


def register_handover_section(builder):
    """Register an additional auto-populated section for every future
    Executive Handover Report. See module docstring for the expected
    return shape. Safe to call multiple times; the same callable won't be
    registered twice."""
    if builder not in _EXTRA_SECTION_BUILDERS:
        _EXTRA_SECTION_BUILDERS.append(builder)
    return builder


def _today():
    return timezone.now().date()


# ─────────────────────────────────────────────────────────────────────────
# Administration grouping
# ─────────────────────────────────────────────────────────────────────────

def _executives_queryset():
    from executives.models import Executive
    return Executive.objects.select_related("member", "elected_via").all()


def _build_administration_base(election, executives):
    """Build the parts of an administration summary that don't depend on
    other administrations: identity, members, and tenure_start. tenure_end
    and is_current/status are filled in afterwards by
    list_administrations(), which is the only place with enough context
    (every other administration's tenure_start) to compute them
    correctly."""
    executives = list(executives)
    start_dates = [e.start_date for e in executives if e.start_date]

    # Tenure start, in priority order:
    #
    # 1. Election.results_applied_at — stamped once, the moment
    #    process_election_results() ran (see elections/models.py). This is
    #    the authoritative anchor for when this administration actually
    #    took office. It deliberately does NOT come from
    #    Executive.start_date: a re-elected officer (same member, same
    #    post) keeps their pre-existing start_date untouched so their own
    #    tenure-in-post reads as continuous, which means min(start_dates)
    #    across the cohort can be stale — even older than the
    #    administration it's supposed to have replaced — whenever at
    #    least one contested post is won by its existing holder. Relying
    #    on that stale date previously caused a completed election whose
    #    winners include a re-elected incumbent to be sorted as "Past"
    #    while an older cohort (e.g. Founding) was wrongly shown as
    #    "Current".
    # 2. min(start_dates) — fallback for elections that predate this field
    #    (results_applied_at is null) and for the Founding administration,
    #    which has no election to anchor to at all.
    # 3. Election.end_date — last resort when there are no executives to
    #    derive a start date from.
    if election is not None and election.results_applied_at:
        tenure_start = election.results_applied_at.date()
    elif start_dates:
        tenure_start = min(start_dates)
    elif election is not None and election.end_date:
        tenure_start = election.end_date.date()
    else:
        tenure_start = None

    key = str(election.pk) if election is not None else FOUNDING_KEY
    name = f"{election.title} Administration" if election is not None else "Founding Administration"

    return {
        "key": key,
        "election": election,
        "name": name,
        "executives": executives,
        "tenure_start": tenure_start,
        "member_count": len(executives),
    }


def list_administrations():
    """Return every administration, chronologically newest-first, for the
    'Previous Administrations' page. This is also the single source of
    truth for tenure_end and Current/Past status: only the single most
    recent administration (by tenure_start) is Current, and every
    administration's tenure_end is bounded by the very next
    administration's tenure_start.

    This deliberately does NOT decide Current/Past per-administration by
    checking whether any of its individual executives still has
    is_current=True — a post that simply wasn't re-contested in a later
    election would keep that executive current forever and wrongly mark
    an otherwise-replaced administration as "Current" too. Only the
    latest election's cohort is ever Current; everything before it is
    Past — which also means every Past administration's report window is
    always cleanly bounded, so it can never leak into the data of
    whichever administration succeeded it."""
    from elections.models import Election

    executives = list(_executives_queryset())
    by_election_id = {}
    founding = []
    for ex in executives:
        if ex.elected_via_id:
            by_election_id.setdefault(ex.elected_via_id, []).append(ex)
        else:
            founding.append(ex)

    elections_map = {
        e.pk: e for e in Election.objects.filter(pk__in=by_election_id.keys())
    }

    administrations = []
    for election_id, execs in by_election_id.items():
        election = elections_map.get(election_id)
        if election is None:
            continue
        administrations.append(_build_administration_base(election, execs))
    if founding:
        administrations.append(_build_administration_base(None, founding))

    # Oldest first so each administration's tenure_end can be chained to
    # the next one's tenure_start. Administrations with no derivable start
    # date (only possible with corrupt/incomplete data) sort first —
    # never treated as "the current one".
    administrations.sort(
        key=lambda a: (a["tenure_start"] is None, a["tenure_start"] or date.min)
    )

    for i, admin in enumerate(administrations):
        is_last = (i == len(administrations) - 1)
        admin["tenure_end"] = None if is_last else administrations[i + 1]["tenure_start"]
        admin["is_current"] = is_last
        admin["status"] = "Current Administration" if is_last else "Past Administration"

    administrations.reverse()  # newest first, for display
    return administrations


def get_administration(key):
    """Return a single administration summary dict for `key`, or None.
    Delegates to list_administrations() so every report always agrees
    with the Previous Administrations list on tenure boundaries and
    Current/Past status — one source of truth, not two."""
    for admin in list_administrations():
        if admin["key"] == key:
            return admin
    return None


def _previous_administration(current):
    """Best-effort lookup of the administration immediately preceding
    `current`, used for the 'Records Handed Over' section."""
    all_admins = list_administrations()
    # all_admins is newest-first with Founding last; find current, take the next one
    for idx, admin in enumerate(all_admins):
        if admin["key"] == current["key"]:
            if idx + 1 < len(all_admins):
                return all_admins[idx + 1]
            return None
    return None


# ─────────────────────────────────────────────────────────────────────────
# Full report assembly
# ─────────────────────────────────────────────────────────────────────────

def build_administration_report(key, limit=200):
    """Build the full context dict for the Executive Handover Report page.
    Returns None if no such administration exists."""
    admin = get_administration(key)
    if admin is None:
        return None

    start = admin["tenure_start"] or date(2020, 1, 1)
    end = admin["tenure_end"] or _today()
    if start > end:
        # Defensive only — with tenure boundaries now derived consistently
        # from Executive.start_date/end_date this shouldn't happen, but an
        # inverted range would silently empty every section below, so guard
        # against it rather than let bad data produce a misleading report.
        start, end = end, start

    report = {"administration": admin}
    report["finance"] = _finance_section(start, end)
    report["projects"] = _projects_section(start, end, limit)
    report["cases"] = _cases_section(start, end, limit)
    report["taskforce"] = _taskforce_section(start, end, limit)
    report["motorcycles"] = _motorcycles_section(start, end, limit)
    report["donation_groups"] = _donation_groups_section(start, end, admin, limit)
    report["donations"] = _donations_section(start, end, limit)
    report["pledges"] = _pledges_section(start, end, limit)
    report["materials_labour"] = _materials_labour_section(start, end, limit)
    report["assets"] = _assets_section(limit)
    report["membership"] = _membership_section(start, end)
    report["elections_conducted"] = _elections_conducted_section(start, end, limit)
    report["achievements"] = _achievements_section(
        start, end, report["finance"], report["projects"], report["cases"],
        report["motorcycles"], report["taskforce"],
    )
    report["handed_over"] = _records_handed_over_section(admin, limit)
    report["extra_sections"] = _run_extra_sections(start, end, admin)

    return report


# ─── Financial Records ─────────────────────────────────────────────────

def _finance_section(start, end):
    from finance.models import Income, Expense, DuesPaymentTransaction
    from project_donations.models import Donation as ProjectDonation
    from operations.models import CaseFile
    from elections.models import HandoverLedger
    from datetime import datetime, time

    # Robust datetime range: covers full days from midnight to 23:59:59
    start_dt = datetime.combine(start, time.min)
    end_dt = datetime.combine(end, time.max)

    # ── INCOME (non-dues, non-project-donation) ──
    income_qs = Income.objects.filter(
        created_at__range=[start_dt, end_dt]
    ).exclude(income_type__in=["DUES", "PROJECT_DONATION"])
    income_agg = income_qs.aggregate(total=Sum("amount"))
    total_income = income_agg["total"] or Decimal("0")

    # ── DUES: use DuesPaymentTransaction.payment_date, NOT DuesPayment.created_at ──
    dues_qs = DuesPaymentTransaction.objects.filter(
        payment_date__range=[start, end]
    )
    dues_agg = dues_qs.aggregate(total=Sum("total_amount"))
    total_dues = dues_agg["total"] or Decimal("0")

    # ── DONATIONS ──
    donation_agg = ProjectDonation.objects.filter(
        status="CONFIRMED", donation_date__range=[start, end]
    ).aggregate(total=Sum("amount"))
    total_donations = donation_agg["total"] or Decimal("0")

    # ── TASKFORCE fines ──
    taskforce_agg = CaseFile.objects.filter(
        status="RESOLVED", resolved_date__range=[start, end]
    ).aggregate(total=Sum("fine_amount"))
    taskforce_revenue = taskforce_agg["total"] or Decimal("0")

    # ── EXPENSES ──
    expense_qs = Expense.objects.filter(created_at__range=[start_dt, end_dt])
    expense_agg = expense_qs.aggregate(total=Sum("amount"))
    total_expenses = expense_agg["total"] or Decimal("0")

    total_revenue = total_income + total_dues + total_donations + taskforce_revenue
    remaining_balance = total_revenue - total_expenses

    ledgers = HandoverLedger.objects.filter(
        tenure_start__gte=start, tenure_end__lte=end
    ).select_related("executive__member")

    bank_balance = sum((l.bank_balance for l in ledgers), Decimal("0"))
    cash_balance = sum((l.cash_balance for l in ledgers), Decimal("0"))
    cash_remaining = sum((l.cash_remaining for l in ledgers), Decimal("0"))

    # Debug counts so you can verify on the page
    debug = {
        "income_count": Income.objects.count(),
        "income_in_range": income_qs.count(),
        "expense_count": Expense.objects.count(),
        "expense_in_range": expense_qs.count(),
        "dues_count": DuesPaymentTransaction.objects.count(),
        "dues_in_range": dues_qs.count(),
    }

    return {
        "total_income": total_income,
        "total_dues": total_dues,
        "total_donations": total_donations,
        "taskforce_revenue": taskforce_revenue,
        "total_revenue": total_revenue,
        "total_expenses": total_expenses,
        "remaining_balance": remaining_balance,
        "bank_balance": bank_balance,
        "cash_balance": cash_balance,
        "cash_remaining": cash_remaining,
        "closing_balance": remaining_balance + bank_balance + cash_balance + cash_remaining,
        "ledgers": ledgers[:50],
        "recent_income": income_qs.select_related("member", "created_by").order_by("-created_at")[:50],
        "recent_expenses": expense_qs.select_related("created_by").order_by("-created_at")[:50],
        "recent_dues": dues_qs.select_related("member", "recorded_by").order_by("-payment_date")[:50],
        "debug": debug,
    }



# ─── Projects ───────────────────────────────────────────────────────────

def _projects_section(start, end, limit):
    from projects.models import Project
    from datetime import datetime, time

    start_dt = datetime.combine(start, time.min)
    end_dt = datetime.combine(end, time.max)

    created_in_tenure = Project.objects.filter(
        created_at__range=[start_dt, end_dt]
    ).order_by("-created_at")[:limit]

    completed_in_tenure = Project.objects.filter(
        status="FINISHED", updated_at__range=[start_dt, end_dt]
    ).order_by("-updated_at")[:limit]

    handed_over_ongoing = Project.objects.filter(status="AT_HAND").order_by("-created_at")[:limit]

    return {
        "created_in_tenure": created_in_tenure,
        "completed_in_tenure": completed_in_tenure,
        "handed_over_ongoing": handed_over_ongoing,
        "counts": {
            "created": Project.objects.filter(created_at__range=[start_dt, end_dt]).count(),
            "completed": Project.objects.filter(
                status="FINISHED", updated_at__range=[start_dt, end_dt]
            ).count(),
            "at_hand": Project.objects.filter(status="AT_HAND").count(),
            "future": Project.objects.filter(status="FUTURE").count(),
        },
        "debug": {
            "total_projects": Project.objects.count(),
            "projects_in_range": created_in_tenure.count(),
        },
    }



# ─── Cases ──────────────────────────────────────────────────────────────

def _cases_section(start, end, limit):
    from operations.models import CaseFile

    handled_qs = CaseFile.objects.filter(
        created_at__date__gte=start, created_at__date__lte=end
    )
    handled = handled_qs.select_related("respondent", "created_by").order_by("-created_at")[:limit]

    resolved_qs = CaseFile.objects.filter(
        status="RESOLVED", resolved_date__gte=start, resolved_date__lte=end
    )
    resolved = resolved_qs.select_related("respondent").order_by("-resolved_date")[:limit]

    pending_handed_over = CaseFile.objects.filter(
        status__in=["OPEN", "IN_PROGRESS"]
    ).select_related("respondent").order_by("-created_at")[:limit]

    return {
        "handled": handled,
        "resolved": resolved,
        "pending_handed_over": pending_handed_over,
        "counts": {
            "handled": handled_qs.count(),
            # Resolved this tenure (by resolution date — may include cases
            # originally filed under an earlier administration).
            "resolved": resolved_qs.count(),
            # Of the cases *filed* during this tenure, how many currently
            # sit in each status — the backlog this administration created.
            "open": handled_qs.filter(status="OPEN").count(),
            "in_progress": handled_qs.filter(status="IN_PROGRESS").count(),
            # Association-wide open/in-progress backlog at report time,
            # regardless of tenure — used by the Records Handed Over section.
            "pending": CaseFile.objects.filter(status__in=["OPEN", "IN_PROGRESS"]).count(),
        },
    }


# ─── Task Force ─────────────────────────────────────────────────────────

def _taskforce_section(start, end, limit):
    from operations.models import TaskForceMember

    created_in_tenure = TaskForceMember.objects.filter(
        assigned_date__gte=start, assigned_date__lte=end
    ).select_related("member").order_by("-assigned_date")[:limit]

    all_current = TaskForceMember.objects.select_related("member").order_by("-assigned_date")[:limit]

    return {
        "created_in_tenure": created_in_tenure,
        "all_current": all_current,
        "counts": {
            "total": TaskForceMember.objects.count(),
            "active": TaskForceMember.objects.filter(is_active=True).count(),
            "inactive": TaskForceMember.objects.filter(is_active=False).count(),
            "established_in_tenure": TaskForceMember.objects.filter(
                assigned_date__gte=start, assigned_date__lte=end
            ).count(),
        },
    }


# ─── Motorcycles ────────────────────────────────────────────────────────

def _motorcycles_section(start, end, limit):
    from operations.models import Motorcycle

    all_motorcycles = Motorcycle.objects.select_related("assigned_to").order_by("asset_tag")[:limit]
    acquired_in_tenure = Motorcycle.objects.filter(
        created_at__date__gte=start, created_at__date__lte=end
    ).select_related("assigned_to")[:limit]

    return {
        "all_motorcycles": all_motorcycles,
        "acquired_in_tenure": acquired_in_tenure,
        "counts": {
            "total": Motorcycle.objects.count(),
            "excellent": Motorcycle.objects.filter(condition="EXCELLENT").count(),
            "needs_service": Motorcycle.objects.filter(condition="NEEDS_SERVICE").count(),
            "grounded": Motorcycle.objects.filter(condition="GROUNDED").count(),
            "acquired": Motorcycle.objects.filter(
                created_at__date__gte=start, created_at__date__lte=end
            ).count(),
        },
    }


# ─── Donation Groups ────────────────────────────────────────────────────

def _donation_groups_section(start, end, admin, limit):
    from settingsapp.models import DonationGroup

    groups = DonationGroup.objects.select_related("created_by").order_by("name")[:limit]
    rows = []
    for g in groups:
        rows.append({
            "group": g,
            "total_realized": g.total_money_donated,
            "member_count": g.member_count,
            "created_in_tenure": bool(
                start <= g.created_at.date() <= end
            ) if g.created_at else False,
        })

    created_in_tenure_count = DonationGroup.objects.filter(
        created_at__date__gte=start, created_at__date__lte=end
    ).count()

    return {
        "rows": rows,
        "counts": {
            "total": DonationGroup.objects.count(),
            "created_in_tenure": created_in_tenure_count,
        },
    }


# ─── Donations ──────────────────────────────────────────────────────────

def _donations_section(start, end, limit):
    from project_donations.models import Donation as ProjectDonation

    in_tenure = ProjectDonation.objects.filter(
        donation_date__gte=start, donation_date__lte=end
    ).select_related("project", "member", "outside_donor").order_by("-donation_date")[:limit]

    agg = ProjectDonation.objects.filter(
        status="CONFIRMED", donation_type="MONEY",
        donation_date__gte=start, donation_date__lte=end
    ).aggregate(
        total_money=Sum("amount"),
        count=Count("id"),
    )

    return {
        "in_tenure": in_tenure,
        "total_amount": agg["total_money"] or Decimal("0"),
        "count": agg["count"] or 0,
    }


# ─── Pledges ────────────────────────────────────────────────────────────

def _pledges_section(start, end, limit):
    from project_donations.models import Pledge
    from datetime import datetime, time

    start_dt = datetime.combine(start, time.min)
    end_dt = datetime.combine(end, time.max)

    in_tenure_qs = Pledge.objects.filter(
        created_at__range=[start_dt, end_dt]
    ).select_related("member", "outside_donor", "project")
    in_tenure = in_tenure_qs.order_by("-created_at")[:limit]

    outstanding_qs = Pledge.objects.exclude(
        status__in=["COMPLETED", "CANCELLED"]
    ).select_related("member", "outside_donor", "project").order_by("-created_at")
    outstanding = outstanding_qs[:limit]

    total_outstanding = sum((p.outstanding_balance for p in outstanding_qs), Decimal("0"))

    value_agg = in_tenure_qs.filter(donation_type="MONEY").aggregate(
        total=Sum("pledged_amount")
    )
    total_pledged_value = value_agg["total"] or Decimal("0")

    return {
        "in_tenure": in_tenure,
        "outstanding": outstanding,
        "total_outstanding": total_outstanding,
        "total_pledged_value": total_pledged_value,
        "counts": {
            "created_in_tenure": in_tenure_qs.count(),
            "outstanding": Pledge.objects.exclude(status__in=["COMPLETED", "CANCELLED"]).count(),
            "money": in_tenure_qs.filter(donation_type="MONEY").count(),
            "material": in_tenure_qs.filter(donation_type="MATERIAL").count(),
            "labour": in_tenure_qs.filter(donation_type="LABOUR").count(),
        },
        "debug": {
            "total_pledges": Pledge.objects.count(),
            "pledges_in_range": in_tenure_qs.count(),
        },
    }



# ─── Materials & Labour ─────────────────────────────────────────────────

def _materials_labour_section(start, end, limit):
    from project_donations.models import Donation as ProjectDonation

    materials = ProjectDonation.objects.filter(
        donation_type="MATERIAL", donation_date__gte=start, donation_date__lte=end
    ).select_related("project", "member", "outside_donor").order_by("-donation_date")[:limit]

    labour = ProjectDonation.objects.filter(
        donation_type="LABOUR", donation_date__gte=start, donation_date__lte=end
    ).select_related("project", "member", "outside_donor").order_by("-donation_date")[:limit]

    value_agg = ProjectDonation.objects.filter(
        donation_type__in=["MATERIAL", "LABOUR"],
        donation_date__gte=start, donation_date__lte=end,
    ).aggregate(total=Sum("estimated_value"))

    return {
        "materials": materials,
        "labour": labour,
        "total_estimated_value": value_agg["total"] or Decimal("0"),
    }


# ─── Assets & Inventory ─────────────────────────────────────────────────

def _assets_section(limit):
    """Assets & Inventory currently tracks motorcycles — the only dedicated
    asset-tracking model in the system. New asset types can hook in via
    register_handover_section()."""
    from operations.models import Motorcycle

    assets = Motorcycle.objects.select_related("assigned_to").order_by("asset_tag")[:limit]
    return {
        "items": [
            {
                "name": f"{m.asset_tag} — {m.brand} {m.model}".strip(),
                "condition": m.get_condition_display(),
                "quantity": 1,
                "status": "Assigned" if m.assigned_to else "In Store",
                "assigned_to": m.assigned_to,
                "handed_over": True,
            }
            for m in assets
        ],
        "count": Motorcycle.objects.count(),
    }


# ─── Membership Statistics ──────────────────────────────────────────────

def _membership_section(start, end):
    from members.models import Member, Clan

    new_registrations = Member.objects.filter(
        created_at__date__gte=start, created_at__date__lte=end
    ).select_related("umu_nna_clan").order_by("-created_at")[:100]

    removed_in_tenure = Member.objects.filter(
        status="REMOVED", updated_at__date__gte=start, updated_at__date__lte=end
    ).select_related("umu_nna_clan").order_by("-updated_at")[:100]

    active_members = Member.objects.filter(status="ACTIVE")
    age_ranges = {
        "18-25": active_members.filter(age__gte=18, age__lte=25).count(),
        "26-35": active_members.filter(age__gte=26, age__lte=35).count(),
        "36-45": active_members.filter(age__gte=36, age__lte=45).count(),
        "46-55": active_members.filter(age__gte=46, age__lte=55).count(),
        "56+": active_members.filter(age__gte=56).count(),
    }

    by_clan = list(
        Clan.objects.annotate(member_count=Count("members")).values("name", "member_count")
    )

    return {
        "new_registrations": new_registrations,
        "removed_in_tenure": removed_in_tenure,
        "age_ranges": age_ranges,
        "by_clan": by_clan,
        "totals": {
            "total_members": Member.objects.count(),
            "active": Member.objects.filter(status="ACTIVE").count(),
            "past_member": Member.objects.filter(status="PAST_MEMBER").count(),
            "removed": Member.objects.filter(status="REMOVED").count(),
            "new_in_tenure": Member.objects.filter(
                created_at__date__gte=start, created_at__date__lte=end
            ).count(),
            "removed_in_tenure": Member.objects.filter(
                status="REMOVED", updated_at__date__gte=start, updated_at__date__lte=end
            ).count(),
        },
    }


# ─── Elections Conducted ────────────────────────────────────────────────

def _elections_conducted_section(start, end, limit):
    from elections.models import Election

    conducted = Election.objects.filter(
        start_date__date__gte=start, start_date__date__lte=end
    ).order_by("-start_date")[:limit]
    return {"items": conducted}


# ─── Achievements (auto-derived) ────────────────────────────────────────

def _achievements_section(start, end, finance, projects, cases, motorcycles, taskforce):
    top_expenses = list(finance["recent_expenses"][:5])
    top_income = list(finance["recent_income"][:5])

    return {
        "projects_completed": projects["counts"]["completed"],
        "funds_raised": finance["total_revenue"],
        "cases_resolved": cases["counts"]["resolved"],
        "assets_acquired": motorcycles["counts"]["acquired"],
        "committees_established": taskforce["counts"]["established_in_tenure"],
        "major_activities": [
            {"label": e.description, "type": "Expense", "amount": e.amount} for e in top_expenses
        ] + [
            {"label": i.reason, "type": "Income", "amount": i.amount} for i in top_income
        ],
    }


# ─── Records Handed Over (from previous administration) ────────────────

def _records_handed_over_section(admin, limit):
    from operations.models import CaseFile
    from projects.models import Project
    from project_donations.models import Pledge
    from elections.models import HandoverLedger

    previous = _previous_administration(admin)

    ledger_entries = HandoverLedger.objects.filter(
        executive__in=[e.id for e in previous["executives"]]
    ).select_related("executive__member") if previous else HandoverLedger.objects.none()

    return {
        "previous_administration": previous,
        "ledger_entries": ledger_entries[:limit] if previous else [],
        "pending_projects": Project.objects.filter(status="AT_HAND").order_by("-created_at")[:limit],
        "pending_cases": CaseFile.objects.filter(
            status__in=["OPEN", "IN_PROGRESS"]
        ).select_related("respondent").order_by("-created_at")[:limit],
        "outstanding_pledges": Pledge.objects.exclude(
            status__in=["COMPLETED", "CANCELLED"]
        ).select_related("member", "outside_donor", "project").order_by("-created_at")[:limit],
    }


# ─── Extensible extra-section registry runner ───────────────────────────

def _run_extra_sections(start, end, admin):
    sections = []
    for builder in _EXTRA_SECTION_BUILDERS:
        try:
            result = builder(start, end, admin)
        except Exception:
            logger.exception("Handover report extra section builder %r failed", builder)
            continue
        if result:
            sections.append(result)
    return sections


# ─── Built-in extra sections: Notifications & Audit Log ────────────────
# These demonstrate the register_handover_section() mechanism and give
# real coverage for the two other historical-record modules in the system
# that aren't already represented above (Requirement #6).

def _notifications_section(start, end, administration):
    from notifications.models import Notification

    items = list(
        Notification.objects.filter(
            created_at__date__gte=start, created_at__date__lte=end
        ).order_by("-created_at")[:100]
    )
    if not items:
        return None
    return {
        "key": "notifications",
        "title": "Notifications & Announcements",
        "description": "Announcements and system notifications raised during this tenure.",
        "type": "list",
        "items": [
            {
                "title": n.title,
                "subtitle": f"{n.get_notification_type_display()} · {n.created_at:%b %d, %Y}",
                "detail": n.message,
            }
            for n in items
        ],
        "count": len(items),
    }


def _audit_log_section(start, end, administration):
    from auditlogs.models import AuditLog

    qs = AuditLog.objects.filter(
        created_at__date__gte=start, created_at__date__lte=end
    )
    total = qs.count()
    if not total:
        return None
    by_action = list(
        qs.values("action").annotate(count=Count("id")).order_by("-count")[:10]
    )
    return {
        "key": "audit_log",
        "title": "Activity Log Summary",
        "description": "System actions recorded during this tenure, grouped by action type.",
        "type": "table",
        "headers": ["Action", "Occurrences"],
        "rows": [[row["action"], row["count"]] for row in by_action],
        "count": total,
    }


register_handover_section(_notifications_section)
register_handover_section(_audit_log_section)