"""Updated views for OYA finance with smart dues allocation."""
import logging
from dashboard.services import invalidate_dashboard_cache
from datetime import datetime, timedelta, date
from decimal import Decimal
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q, Sum, Count, Max, Value, DecimalField
from django.db.models.functions import Coalesce
from django.utils import timezone
from django.http import JsonResponse
from django.db import transaction
from auditlogs.services import log_action
from accounts.models import User
from core.utils import exclude_admin_users
from .models import Income, Expense, DuesPayment, DuesPaymentTransaction
from project_donations.models import Donation as ProjectDonation, OutsideDonor
from .forms import IncomeForm, ExpenseForm, DuesPaymentAllocationForm

logger = logging.getLogger("oya")

PLATFORM_START_YEAR = 2020
YEARLY_DUES = 5000


# ============================================================
# DONATIONS / OTHER CONTRIBUTIONS
# ============================================================

@login_required
def donation_list(request):
    """List all non-dues income (donations, events, other)."""
    queryset = Income.objects.exclude(income_type__in=["DUES", "PROJECT_DONATION"]).select_related("created_by", "member")

    search_term = request.GET.get("search", "")
    if search_term:
        queryset = queryset.filter(
            Q(reason__icontains=search_term) |
            Q(paid_by__icontains=search_term) |
            Q(member__full_name__icontains=search_term) |
            Q(created_by__full_name__icontains=search_term)
        )

    type_filter = request.GET.get("type", "")
    if type_filter:
        queryset = queryset.filter(income_type=type_filter)

    date_from = request.GET.get("date_from", "")
    date_to = request.GET.get("date_to", "")
    if date_from:
        queryset = queryset.filter(created_at__date__gte=date_from)
    if date_to:
        queryset = queryset.filter(created_at__date__lte=date_to)

    paginator = Paginator(queryset, 10)
    page = request.GET.get("page", 1)
    donations = paginator.get_page(page)

    total_donations = Income.objects.exclude(income_type__in=["DUES", "PROJECT_DONATION"]).aggregate(
        total=Sum("amount")
    )["total"] or 0

    # Add confirmed project donations to donation totals
    total_project_donations = ProjectDonation.objects.filter(
        status="CONFIRMED"
    ).aggregate(
        total=Coalesce(Sum("amount"), Value(0, output_field=DecimalField()))
    )["total"]
    total_donations = total_donations + total_project_donations

    now = timezone.now()
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    this_month_donations = Income.objects.exclude(income_type__in=["DUES", "PROJECT_DONATION"]).filter(
        created_at__gte=month_start
    ).aggregate(total=Sum("amount"))["total"] or 0

    this_month_project_donations = ProjectDonation.objects.filter(
        status="CONFIRMED",
        donation_date__gte=month_start,
    ).aggregate(
        total=Coalesce(Sum("amount"), Value(0, output_field=DecimalField()))
    )["total"]
    this_month_donations = this_month_donations + this_month_project_donations

    total_records = Income.objects.exclude(income_type__in=["DUES", "PROJECT_DONATION"]).count()

    # ─── PROJECT DONATIONS LIST (includes outside donors) ───
    project_donation_qs = ProjectDonation.objects.filter(
        status="CONFIRMED"
    ).select_related("project", "member", "outside_donor", "invited_by")

    if search_term:
        project_donation_qs = project_donation_qs.filter(
            Q(narration__icontains=search_term) |
            Q(reference_number__icontains=search_term) |
            Q(project__title__icontains=search_term) |
            Q(member__full_name__icontains=search_term) |
            Q(outside_donor__full_name__icontains=search_term) |
            Q(invited_by__full_name__icontains=search_term)
        )
    if date_from:
        project_donation_qs = project_donation_qs.filter(donation_date__gte=date_from)
    if date_to:
        project_donation_qs = project_donation_qs.filter(donation_date__lte=date_to)

    project_donation_paginator = Paginator(project_donation_qs, 10)
    project_donation_page = request.GET.get("project_page", 1)
    project_donation_incomes = project_donation_paginator.get_page(project_donation_page)

    context = {
        "donations": donations,
        "project_donation_incomes": project_donation_incomes,
        "search_term": search_term,
        "type_filter": type_filter,
        "income_types": [c for c in Income.INCOME_TYPE_CHOICES if c[0] != "DUES"],
        "date_from": date_from,
        "date_to": date_to,
        "total_donations": total_donations,
        "this_month_donations": this_month_donations,
        "total_records": total_records,
    }
    return render(request, "finance/donation_list.html", context)


# ============================================================
# DUES TRACKER
# ============================================================

@login_required
def dues_tracker(request):
    """Full member x year grid showing dues payment status."""
    from django.db.models import Sum, Case, When, F, Value, DecimalField, Count
    from django.db.models.functions import Coalesce

    current_year = timezone.now().year
    years = list(range(PLATFORM_START_YEAR, current_year + 1))

    # Include all registered members in dues tracking.
    # Exclude Admin accounts — only real members (Floor Members and
    # Executives) should appear; Admins manage/monitor, they don't pay dues.
    members = list(
        exclude_admin_users(
            User.objects.filter(
                serial_number__isnull=False
            ).exclude(
                serial_number=""
            )
        ).order_by("full_name")
    )

    # ONE query: all dues payments, grouped by member — replaces the N x 4-query loop.
    dues_map = {}
    for dp in DuesPayment.objects.select_related("member").all():
        dues_map[(dp.member_id, dp.year)] = dp

    # ONE query: per-member paid/prepaid totals, computed with conditional aggregation
    # instead of 4 queries x N members.
    per_member_totals = (
        DuesPayment.objects.filter(member__in=members)
        .values("member_id")
        .annotate(
            total_paid=Coalesce(
                Sum(Case(When(year__lte=current_year, then=F("amount_paid")),
                         default=Value(0), output_field=DecimalField())),
                Value(0), output_field=DecimalField(),
            ),
            prepaid_paid=Coalesce(
                Sum(Case(When(year__gt=current_year, then=F("amount_paid")),
                         default=Value(0), output_field=DecimalField())),
                Value(0), output_field=DecimalField(),
            ),
        )
    )
    totals_by_member = {row["member_id"]: row for row in per_member_totals}

    member_rows = []
    total_dues_collected = Decimal("0")
    total_dues_expected = Decimal("0")
    total_possible_dues = Decimal("0")

    for member in members:
        join_year = DuesPayment.get_member_join_year(member)  # pure Python, no query
        start_year = max(join_year, PLATFORM_START_YEAR)
        expected_years = current_year - start_year + 1
        total_possible_dues += expected_years * YEARLY_DUES

        totals = totals_by_member.get(member.id, {"total_paid": Decimal("0"), "prepaid_paid": Decimal("0")})
        total_expected_for_member = expected_years * DuesPayment.YEARLY_DUES_AMOUNT
        debt_owed = max(total_expected_for_member - totals["total_paid"], Decimal("0"))

        row = {
            "member": member,
            "years": {},
            "total_debt": debt_owed,
            "join_year": join_year,
        }

        years_paid_count = 0
        years_partial_count = 0
        for year in years:
            key = (member.id, year)
            if year < join_year:
                row["years"][year] = {
                    "status": DuesPayment.STATUS_NOT_APPLICABLE,
                    "payment": None,
                    "amount_paid": Decimal("0"),
                    "remaining": Decimal("0"),
                    "before_join": True,
                }
            elif key in dues_map:
                dp = dues_map[key]
                row["years"][year] = {
                    "status": dp.status,
                    "payment": dp,
                    "amount_paid": dp.amount_paid,
                    "remaining": dp.remaining_balance,
                    "before_join": False,
                }
                total_dues_collected += dp.amount_paid
                if dp.is_fully_paid:
                    years_paid_count += 1
                elif dp.amount_paid > 0:
                    years_partial_count += 1
            else:
                row["years"][year] = {
                    "status": DuesPayment.STATUS_OWED,
                    "payment": None,
                    "amount_paid": Decimal("0"),
                    "remaining": Decimal(str(YEARLY_DUES)),
                    "before_join": False,
                }
                total_dues_expected += YEARLY_DUES

        row["years_paid_count"] = years_paid_count
        row["years_partial_count"] = years_partial_count
        member_rows.append(row)

    # Prepaid dues (future years fully paid) — cash already received
    total_prepaid = DuesPayment.objects.filter(
        year__gt=current_year,
        amount_paid__gte=YEARLY_DUES,
    ).aggregate(
        total=Coalesce(Sum("amount_paid"), Value(0, output_field=DecimalField()))
    )["total"] or Decimal("0")
    total_dues_collected += total_prepaid

    active_members_count = len(members)
    collection_rate = round(
        float(total_dues_collected) / float(total_possible_dues) * 100, 1
    ) if total_possible_dues > 0 else 0

    this_year_paid = DuesPayment.objects.filter(
        year=current_year,
        amount_paid__gte=YEARLY_DUES,
    ).count()
    this_year_expected = active_members_count
    this_year_rate = round(
        (this_year_paid / this_year_expected * 100), 1
    ) if this_year_expected > 0 else 0

    context = {
        "years": years,
        "member_rows": member_rows,
        "current_year": current_year,
        "yearly_dues": YEARLY_DUES,
        "total_dues_collected": total_dues_collected,
        "total_dues_expected": total_dues_expected,
        "total_possible_dues": total_possible_dues,
        "collection_rate": collection_rate,
        "this_year_paid": this_year_paid,
        "this_year_expected": this_year_expected,
        "this_year_rate": this_year_rate,
        "active_members_count": active_members_count,
        "total_prepaid": total_prepaid,
    }
    return render(request, "finance/dues_tracker.html", context)

@login_required
def dues_allocate(request):
    """Smart dues payment allocation — auto-distributes across years."""
    if not request.user.has_executive_access():
        messages.error(request, "Executive access required.")
        invalidate_dashboard_cache()
        return redirect("finance:dues_tracker")

    if request.method == "POST":
        form = DuesPaymentAllocationForm(request.POST, recorded_by=request.user)
        if form.is_valid():
            try:
                with transaction.atomic():
                    result = form.allocate()

                # Log the action
                tx = result["transaction"]
                allocation_summary = ", ".join(
                    f"{a['year']}: ₦{a['allocated']:,.2f}"
                    for a in result["allocations"]
                )
                log_action(
                    user=request.user,
                    action="CREATE",
                    object_type="DuesPaymentTransaction",
                    object_id=tx.id,
                    ip_address=getattr(request, "client_ip", ""),
                    description=(
                        f"Allocated dues payment: {tx.member.get_full_name()} — "
                        f"₦{tx.total_amount:,.2f} → [{allocation_summary}]"
                    ),
                )

                # Show user-friendly messages
                for msg in result["messages"]:
                    messages.info(request, msg)

                messages.success(
                    request,
                    f"Successfully allocated ₦{result['total_allocated']:,.2f} "
                    f"for {tx.member.get_full_name()}."
                )
                if result["remaining"] > 0:
                    messages.warning(
                        request,
                        f"₦{result['remaining']:,.2f} could not be allocated."
                    )

            

            except Exception as e:
                logger.exception("Dues allocation failed")
                messages.error(request, f"Allocation failed: {str(e)}")
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field}: {error}")
    else:
        form = DuesPaymentAllocationForm(recorded_by=request.user)

    return render(request, "finance/dues_form.html", {
        "form": form,
        "title": "Record Dues Payment",
        "action": "Allocate Payment",
        "yearly_dues": YEARLY_DUES,
    })


@login_required
def member_dues_detail(request, member_id):
    """Show detailed dues history and debt for a single member."""
    member = get_object_or_404(User, pk=member_id)
    current_year = timezone.now().year

    # Get join year to determine range
    join_year = DuesPayment.get_member_join_year(member)
    start_year = PLATFORM_START_YEAR  # Always show from platform start for context

    # Include future prepaid years in the display
    max_year = max(
        current_year,
        DuesPayment.objects.filter(member=member).aggregate(
            max_year=Coalesce(Max("year"), Value(current_year))
        )["max_year"]
    )

    years = list(range(start_year, max_year + 1))

    debt_info = DuesPayment.get_member_debt(member)
    payments = DuesPayment.objects.filter(member=member).select_related(
        "recorded_by", "income"
    ).order_by("-year")

    year_status = []
    for year in years:
        # Years before join year are marked as N/A
        if year < join_year:
            year_status.append({
                "year": year,
                "status": DuesPayment.STATUS_NOT_APPLICABLE,
                "payment": None,
                "is_future": year > current_year,
                "before_join": True,
            })
        else:
            payment = payments.filter(year=year).first()
            year_status.append({
                "year": year,
                "status": payment.status if payment else DuesPayment.STATUS_OWED,
                "payment": payment,
                "is_future": year > current_year,
                "before_join": False,
            })

    # Get payment transactions for this member
    transactions = DuesPaymentTransaction.objects.filter(
        member=member
    ).select_related("recorded_by").order_by("-payment_date")[:20]

    context = {
        "member": member,
        "year_status": year_status,
        "debt_info": debt_info,
        "payments": payments,
        "transactions": transactions,
        "yearly_dues": YEARLY_DUES,
        "current_year": current_year,
        "join_year": join_year,
    }
    return render(request, "finance/member_dues_detail.html", context)



@login_required
def dues_delete(request, pk):
    """Delete a dues payment record (and its linked income)."""
    if not request.user.has_admin_access():
        messages.error(request, "Admin access required.")
        invalidate_dashboard_cache()
        return redirect("finance:dues_tracker")

    dues = get_object_or_404(DuesPayment.objects.select_related("member", "income"), pk=pk)

    if request.method == "POST":
        member_name = dues.member.get_full_name()
        year = dues.year
        if dues.income:
            dues.income.delete()
        dues.delete()
        log_action(
            user=request.user,
            action="DELETE",
            object_type="DuesPayment",
            object_id=pk,
            ip_address=getattr(request, "client_ip", ""),
            description=f"Deleted dues record: {member_name} - {year}"
        )
        messages.success(request, f"Dues record deleted for {member_name} - {year}.")
        invalidate_dashboard_cache()
        return redirect("finance:dues_tracker")

    return render(request, "finance/dues_confirm_delete.html", {"dues": dues})


# ============================================================
# INCOME LIST (SPLIT: DUES + DONATIONS)
# ============================================================

@login_required
def income_list(request):
    """List all income records split by Dues (grouped by transaction) and Donations with totals."""

    # --- DUES (grouped by DuesPaymentTransaction) ---
    dues_txns_qs = DuesPaymentTransaction.objects.select_related(
        "member", "recorded_by"
    ).order_by("-payment_date")

    # --- DONATIONS & OTHER (non-dues income) ---
    donation_qs = Income.objects.exclude(income_type__in=["DUES", "PROJECT_DONATION"]).select_related("created_by", "member")

    # Search/filter
    search_term = request.GET.get("search", "")
    if search_term:
        donation_qs = donation_qs.filter(
            Q(reason__icontains=search_term) |
            Q(paid_by__icontains=search_term) |
            Q(member__full_name__icontains=search_term) |
            Q(created_by__full_name__icontains=search_term)
        )
        dues_txns_qs = dues_txns_qs.filter(
            Q(member__full_name__icontains=search_term) |
            Q(receipt_reference__icontains=search_term) |
            Q(recorded_by__full_name__icontains=search_term)
        )

    type_filter = request.GET.get("type", "")
    if type_filter:
        donation_qs = donation_qs.filter(income_type=type_filter)

    date_from = request.GET.get("date_from", "")
    date_to = request.GET.get("date_to", "")
    if date_from:
        donation_qs = donation_qs.filter(created_at__date__gte=date_from)
        dues_txns_qs = dues_txns_qs.filter(payment_date__gte=date_from)
    if date_to:
        donation_qs = donation_qs.filter(created_at__date__lte=date_to)
        dues_txns_qs = dues_txns_qs.filter(payment_date__lte=date_to)

    from django.db.models import Prefetch

    # Build grouped dues data for display
    current_year = timezone.now().year

    # Prefetch related DuesPayment records to eliminate N+1 queries
    dues_txns_qs = dues_txns_qs.prefetch_related(
        Prefetch("dues_allocations", queryset=DuesPayment.objects.order_by("year"))
    )

    # Paginate the QUERYSET first — only 10 rows hit the loop
    dues_paginator = Paginator(dues_txns_qs, 10)
    dues_page_num = request.GET.get("dues_page", 1)
    dues_page = dues_paginator.get_page(dues_page_num)

    dues_grouped = []
    for txn in dues_page.object_list:
        years_list = [dp.year for dp in txn.dues_allocations.all()]
        if years_list:
            if len(years_list) == 1:
                year_display = str(years_list[0])
                reason = f"Yearly Dues — {year_display}"
            else:
                year_display = f"{years_list[0]}–{years_list[-1]}"
                has_prepaid = any(y > current_year for y in years_list)
                prepaid_label = " (Prepaid)" if has_prepaid else ""
                reason = f"Yearly Dues — {year_display}{prepaid_label}"
        else:
            reason = "Yearly Dues"

        dues_grouped.append({
            "transaction": txn,
            "reason": reason,
            "amount": txn.total_amount,
            "member": txn.member,
            "recorded_by": txn.recorded_by,
            "payment_date": txn.payment_date,
            "years": years_list,
            "is_prepaid": any(y > current_year for y in years_list) if years_list else False,
        })

    # Swap the page's raw objects with the enriched dicts — zero template changes needed
    dues_page.object_list = dues_grouped
    dues_incomes = dues_page

    # Pagination for DONATIONS
    donation_paginator = Paginator(donation_qs, 10)
    donation_page = request.GET.get("page", 1)
    donation_incomes = donation_paginator.get_page(donation_page)

    # ─── PROJECT DONATIONS (outside donors + members) ───
    project_donation_qs = ProjectDonation.objects.filter(
        status="CONFIRMED"
    ).select_related("project", "member", "outside_donor", "invited_by")

    if search_term:
        project_donation_qs = project_donation_qs.filter(
            Q(narration__icontains=search_term) |
            Q(reference_number__icontains=search_term) |
            Q(project__title__icontains=search_term) |
            Q(member__full_name__icontains=search_term) |
            Q(outside_donor__full_name__icontains=search_term) |
            Q(invited_by__full_name__icontains=search_term)
        )
    if date_from:
        project_donation_qs = project_donation_qs.filter(donation_date__gte=date_from)
    if date_to:
        project_donation_qs = project_donation_qs.filter(donation_date__lte=date_to)

    project_donation_paginator = Paginator(project_donation_qs, 10)
    project_donation_page = request.GET.get("project_page", 1)
    project_donation_incomes = project_donation_paginator.get_page(project_donation_page)

    # Totals (use full QS, not paginated)
    total_dues = Income.objects.filter(income_type="DUES").aggregate(
        total=Coalesce(Sum("amount"), Value(0, output_field=DecimalField()))
    )["total"] or Decimal("0")

    # ─── ADD PREPAID DUES TO TOTAL DUES COLLECTED ───
    total_prepaid = DuesPayment.objects.filter(
        year__gt=current_year,
        amount_paid__gte=YEARLY_DUES,
    ).aggregate(
        total=Coalesce(Sum("amount_paid"), Value(0, output_field=DecimalField()))
    )["total"] or Decimal("0")
    total_dues = total_dues + total_prepaid
    # ─────────────────────────────────────────────────

    total_donations_income = Income.objects.exclude(income_type__in=["DUES", "PROJECT_DONATION"]).aggregate(
        total=Coalesce(Sum("amount"), Value(0, output_field=DecimalField()))
    )["total"] or Decimal("0")

    total_project_donations = ProjectDonation.objects.filter(
        status="CONFIRMED"
    ).aggregate(
        total=Coalesce(Sum("amount"), Value(0, output_field=DecimalField()))
    )["total"] or Decimal("0")

    # Include outside donor project donations in donation totals
    total_donations = total_donations_income + total_project_donations
    total_income = total_dues + total_donations
    total_records = Income.objects.count()

    context = {
        "dues_incomes": dues_incomes,
        "donation_incomes": donation_incomes,
        "project_donation_incomes": project_donation_incomes,
        "search_term": search_term,
        "type_filter": type_filter,
        "date_from": date_from,
        "date_to": date_to,
        "total_dues": total_dues,
        "total_donations": total_donations,
        "total_project_donations": total_project_donations,
        "total_income": total_income,
        "total_records": total_records,
        "total_prepaid": total_prepaid,
    }
    return render(request, "finance/income_list.html", context)


@login_required
def income_create(request):
    """Create a new non-dues income record with member search."""
    if not request.user.has_executive_access():
        messages.error(request, "Executive access required.")
        return redirect("finance:donation_list")

     # ─── TREASURY BALANCE (all money collected minus expenses) ───
    total_income = Income.objects.exclude(income_type="PROJECT_DONATION").aggregate(
        total=Coalesce(Sum("amount"), Value(0, output_field=DecimalField()))
    )["total"] or Decimal("0")

    total_project_donations = ProjectDonation.objects.filter(
        status="CONFIRMED"
    ).aggregate(
        total=Coalesce(Sum("amount"), Value(0, output_field=DecimalField()))
    )["total"] or Decimal("0")
    total_income += total_project_donations

    # Add prepaid dues (future years fully paid) — cash already received
    current_year = timezone.now().year
    total_prepaid = DuesPayment.objects.filter(
        year__gt=current_year,
        amount_paid__gte=YEARLY_DUES,
    ).aggregate(
        total=Coalesce(Sum("amount_paid"), Value(0, output_field=DecimalField()))
    )["total"] or Decimal("0")
    total_income += total_prepaid

    total_expenses = Expense.objects.aggregate(
        total=Coalesce(Sum("amount"), Value(0, output_field=DecimalField()))
    )["total"] or Decimal("0")
    treasury_balance = total_income - total_expenses
    # ─────────────────────────────────────────────────────────────


    recent_incomes = Income.objects.exclude(income_type__in=["DUES", "PROJECT_DONATION"]).select_related("created_by", "member").order_by("-created_at")[:5]

    thirty_days_ago = timezone.now() - timedelta(days=30)
    common_reasons = (
        Income.objects.exclude(income_type__in=["DUES", "PROJECT_DONATION"]).filter(created_at__gte=thirty_days_ago)
        .values("reason")
        .annotate(count=Count("id"))
        .order_by("-count")
        .values_list("reason", flat=True)[:5]
    )

    if request.method == "POST":
        form = IncomeForm(request.POST)
        if form.is_valid():
            income = form.save(commit=False)
            income.created_by = request.user
            income.save()
            log_action(
                user=request.user,
                action="CREATE",
                object_type="Income",
                object_id=income.id,
                ip_address=getattr(request, "client_ip", ""),
                description=f"Recorded {income.get_income_type_display()}: ₦{income.amount:,.2f} - {income.reason} (by {income.get_payer_display()})"
            )
            messages.success(request, "Income recorded successfully.")
            invalidate_dashboard_cache()
            return redirect("finance:donation_list")
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field}: {error}")
    else:
        form = IncomeForm()

    return render(request, "finance/income_form.html", {
        "form": form,
        "title": "Record Contribution",
        "action": "Save",
        "treasury_balance": treasury_balance,
        "total_income": total_income,
        "total_expenses": total_expenses,
        "recent_incomes": recent_incomes,
        "common_reasons": list(common_reasons),
        "total_prepaid": total_prepaid,   # ← add this
    })



@login_required
def income_detail(request, pk):
    """Display income details."""
    income = get_object_or_404(Income.objects.select_related("created_by", "member"), pk=pk)
    return render(request, "finance/income_detail.html", {"income": income})


@login_required
def income_delete(request, pk):
    """Delete an income record."""
    if not request.user.has_admin_access():
        messages.error(request, "Admin access required.")
        return redirect("finance:donation_list")

    income = get_object_or_404(Income, pk=pk)

    if request.method == "POST":
        amount = income.amount
        reason = income.reason
        income_type = income.get_income_type_display()

        # If this income is auto-linked to a project donation, delete the
        # project donation too so both apps stay in sync. The donation signal
        # will also remove the linked income record.
        project_donation = getattr(income, 'project_donation', None)
        if project_donation:
            project_donation.delete()
        else:
            income.delete()

        log_action(
            user=request.user,
            action="DELETE",
            object_type="Income",
            object_id=pk,
            ip_address=getattr(request, "client_ip", ""),
            description=f"Deleted {income_type}: ₦{amount:,.2f} - {reason}"
        )
        messages.success(request, "Income record deleted.")
        invalidate_dashboard_cache()
        return redirect("finance:donation_list")

    return render(request, "finance/income_confirm_delete.html", {"income": income})


# ============================================================
# EXPENSES
# ============================================================

@login_required
def expense_list(request):
    """List all expense records with search and pagination."""
    queryset = Expense.objects.select_related("created_by").all()

    search_term = request.GET.get("search", "")
    if search_term:
        queryset = queryset.filter(
            Q(description__icontains=search_term) |
            Q(category__icontains=search_term) |
            Q(created_by__full_name__icontains=search_term)
        )

    category_filter = request.GET.get("category", "")
    if category_filter:
        queryset = queryset.filter(category=category_filter)

    date_from = request.GET.get("date_from", "")
    date_to = request.GET.get("date_to", "")
    if date_from:
        queryset = queryset.filter(created_at__date__gte=date_from)
    if date_to:
        queryset = queryset.filter(created_at__date__lte=date_to)

    paginator = Paginator(queryset, 10)
    page = request.GET.get("page", 1)
    expenses = paginator.get_page(page)

    total_expenses = Expense.objects.aggregate(total=Sum("amount"))["total"] or 0

    now = timezone.now()
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    this_month_expenses = Expense.objects.filter(
        created_at__gte=month_start
    ).aggregate(total=Sum("amount"))["total"] or 0

    total_records = Expense.objects.count()
    # ─── TREASURY BALANCE (all money collected minus expenses) ───
    total_income = Income.objects.exclude(income_type="PROJECT_DONATION").aggregate(
        total=Coalesce(Sum("amount"), Value(0, output_field=DecimalField()))
    )["total"] or Decimal("0")

    total_project_donations = ProjectDonation.objects.filter(
        status="CONFIRMED"
    ).aggregate(
        total=Coalesce(Sum("amount"), Value(0, output_field=DecimalField()))
    )["total"] or Decimal("0")
    total_income += total_project_donations

    # Add prepaid dues (future years fully paid) — cash already received
    current_year = timezone.now().year
    total_prepaid = DuesPayment.objects.filter(
        year__gt=current_year,
        amount_paid__gte=YEARLY_DUES,
    ).aggregate(
        total=Coalesce(Sum("amount_paid"), Value(0, output_field=DecimalField()))
    )["total"] or Decimal("0")
    total_income += total_prepaid

    total_expenses = Expense.objects.aggregate(
        total=Coalesce(Sum("amount"), Value(0, output_field=DecimalField()))
    )["total"] or Decimal("0")
    treasury_balance = total_income - total_expenses
    # ─────────────────────────────────────────────────────────────
    context = {
        "expenses": expenses,
        "search_term": search_term,
        "category_filter": category_filter,
        "category_choices": Expense.CATEGORY_CHOICES,
        "date_from": date_from,
        "date_to": date_to,
        "total_expenses": total_expenses,
        "this_month_expenses": this_month_expenses,
        "total_records": total_records,
        "treasury_balance": treasury_balance,
        "total_prepaid": total_prepaid,   # ← add this
    }

    return render(request, "finance/expense_list.html", context)

@login_required
def expense_create(request):
    """Create a new expense record."""
    if not request.user.has_executive_access():
        messages.error(request, "Executive access required.")
        return redirect("finance:expense_list")

    # ─── TREASURY BALANCE (all money collected minus expenses) ───
    total_income = Income.objects.exclude(income_type="PROJECT_DONATION").aggregate(
        total=Coalesce(Sum("amount"), Value(0, output_field=DecimalField()))
    )["total"] or Decimal("0")

    total_project_donations = ProjectDonation.objects.filter(
        status="CONFIRMED"
    ).aggregate(
        total=Coalesce(Sum("amount"), Value(0, output_field=DecimalField()))
    )["total"] or Decimal("0")
    total_income += total_project_donations

    # Add prepaid dues (future years fully paid) — cash already received
    current_year = timezone.now().year
    total_prepaid = DuesPayment.objects.filter(
        year__gt=current_year,
        amount_paid__gte=YEARLY_DUES,
    ).aggregate(
        total=Coalesce(Sum("amount_paid"), Value(0, output_field=DecimalField()))
    )["total"] or Decimal("0")
    total_income += total_prepaid

    total_expenses = Expense.objects.aggregate(
        total=Coalesce(Sum("amount"), Value(0, output_field=DecimalField()))
    )["total"] or Decimal("0")
    treasury_balance = total_income - total_expenses
    # ─────────────────────────────────────────────────────────────


    recent_expenses = Expense.objects.select_related("created_by").order_by("-created_at")[:5]

    thirty_days_ago = timezone.now() - timedelta(days=30)
    common_categories = (
        Expense.objects.filter(created_at__gte=thirty_days_ago)
        .values("category")
        .annotate(count=Count("id"))
        .order_by("-count")
        .values_list("category", flat=True)[:5]
    )

    if request.method == "POST":
        form = ExpenseForm(request.POST, request.FILES)
        if form.is_valid():
            expense = form.save(commit=False)
            expense.created_by = request.user
            expense.save()
            log_action(
                user=request.user,
                action="CREATE",
                object_type="Expense",
                object_id=expense.id,
                ip_address=getattr(request, "client_ip", ""),
                description=f"Recorded expense: ₦{expense.amount:,.2f} - {expense.category}"
            )
            messages.success(request, "Expense recorded successfully.")
            invalidate_dashboard_cache()
            return redirect("finance:expense_list")
        else:
            for error in form.errors.values():
                messages.error(request, error)
    else:
        form = ExpenseForm()

    return render(request, "finance/expense_form.html", {
        "form": form,
        "title": "Record Expense",
        "action": "Save",
        "treasury_balance": treasury_balance,
        "total_income": total_income,
        "total_expenses": total_expenses,
        "recent_expenses": recent_expenses,
        "common_categories": list(common_categories),
        "total_prepaid": total_prepaid,   # ← add this
    })



@login_required
def expense_detail(request, pk):
    """Display expense details."""
    expense = get_object_or_404(Expense.objects.select_related("created_by"), pk=pk)
    return render(request, "finance/expense_detail.html", {"expense": expense})


@login_required
def expense_delete(request, pk):
    """Delete an expense record."""
    if not request.user.has_admin_access():
        messages.error(request, "Admin access required.")
        return redirect("finance:expense_list")

    expense = get_object_or_404(Expense, pk=pk)

    if request.method == "POST":
        amount = expense.amount
        category = expense.category
        expense.delete()
        log_action(
            user=request.user,
            action="DELETE",
            object_type="Expense",
            object_id=pk,
            ip_address=getattr(request, "client_ip", ""),
            description=f"Deleted expense: ₦{amount:,.2f} - {category}"
        )
        messages.success(request, "Expense record deleted.")
        invalidate_dashboard_cache()
        return redirect("finance:expense_list")

    return render(request, "finance/expense_confirm_delete.html", {"expense": expense})


# ============================================================
# FINANCE SUMMARY / DASHBOARD
# ============================================================
@login_required
def finance_summary(request):
    """Display financial summary with split KPIs."""
    current_year = timezone.now().year

    total_dues = Income.objects.filter(income_type="DUES").aggregate(
        total=Sum("amount")
    )["total"] or 0

    # ─── ADD PREPAID DUES TO TOTAL DUES COLLECTED ───
    total_prepaid = DuesPayment.objects.filter(
        year__gt=current_year,
        amount_paid__gte=YEARLY_DUES,
    ).aggregate(
        total=Coalesce(Sum("amount_paid"), Value(0, output_field=DecimalField()))
    )["total"] or Decimal("0")
    total_dues = total_dues + total_prepaid
    # ─────────────────────────────────────────────────

    total_donations_income = Income.objects.exclude(income_type__in=["DUES", "PROJECT_DONATION"]).aggregate(
        total=Sum("amount")
    )["total"] or 0

    # Include confirmed project donations (from outside donors & members) in totals
    total_project_donations = ProjectDonation.objects.filter(
        status="CONFIRMED"
    ).aggregate(
        total=Coalesce(Sum("amount"), Value(0, output_field=DecimalField()))
    )["total"] or Decimal("0")

    total_donations = total_donations_income + total_project_donations
    total_income = total_dues + total_donations
    total_expenses = Expense.objects.aggregate(total=Sum("amount"))["total"] or 0
    treasury_balance = total_income - total_expenses

    # Count only registered members (Admins manage/monitor — excluded;
    # Executives are still members and remain counted).
    active_members = exclude_admin_users(
        User.objects.filter(
            is_active=True,
            serial_number__isnull=False
        ).exclude(
            serial_number=""
        )
    ).count()

    years_count = current_year - PLATFORM_START_YEAR + 1
    total_dues_possible = active_members * years_count * YEARLY_DUES
    dues_collection_rate = round((total_dues / total_dues_possible * 100), 1) if total_dues_possible > 0 else 0

    this_year_dues_paid = DuesPayment.objects.filter(
        year=current_year,
        amount_paid__gte=YEARLY_DUES,
    ).count()
    this_year_dues_rate = round((this_year_dues_paid / active_members * 100), 1) if active_members > 0 else 0

    expenses_raw = Expense.objects.values("category").annotate(
        total=Sum("amount")
    ).order_by("-total")

    expenses_by_category = []
    for item in expenses_raw:
        percentage = round((item["total"] / total_expenses * 100), 1) if total_expenses > 0 else 0
        expenses_by_category.append({
            "category": dict(Expense.CATEGORY_CHOICES).get(item["category"], item["category"]),
            "total": item["total"],
            "percentage": percentage,
        })

        # ===================================================================
    # FIX: Group dues payments by transaction instead of showing each year
    # ===================================================================

    recent_dues_txns = DuesPaymentTransaction.objects.select_related(
        "member", "recorded_by"
    ).order_by("-payment_date")[:5]

    recent_donations = Income.objects.exclude(
        income_type__in=["DUES", "PROJECT_DONATION"]
    ).select_related("created_by", "member").order_by("-created_at")[:5]

    recent_expenses = Expense.objects.select_related("created_by").order_by("-created_at")[:5]

    recent_transactions = []

    for txn in recent_dues_txns:
        dues_records = DuesPayment.objects.filter(
            transactions=txn
        ).values_list("year", flat=True).order_by("year")

        years_list = list(dues_records)
        if years_list:
            if len(years_list) == 1:
                year_display = str(years_list[0])
                description = f"Yearly Dues {year_display}"
            else:
                year_display = f"{years_list[0]}–{years_list[-1]}"
                has_prepaid = any(y > current_year for y in years_list)
                prepaid_label = " (Prepaid)" if has_prepaid else ""
                description = f"Yearly Dues ({year_display}){prepaid_label}"
        else:
            description = "Yearly Dues"

        # Normalize payment_date to aware datetime for consistent sorting
        payment_dt = txn.payment_date
        if isinstance(payment_dt, date) and not isinstance(payment_dt, datetime):
            payment_dt = datetime.combine(payment_dt, datetime.min.time())
        # Make naive datetime aware (match Django's timezone-aware datetimes)
        if payment_dt.tzinfo is None:
            payment_dt = timezone.make_aware(payment_dt)

        recent_transactions.append({
            "type": "dues_transaction",
            "amount": txn.total_amount,
            "description": description,
            "reason": description,
            "created_at": payment_dt,
            "payment_date": txn.payment_date,
            "member": txn.member,
            "recorded_by": txn.recorded_by,
            "transaction_id": txn.id,
            "income_type": "DUES",
            "years": years_list,
            "is_prepaid": any(y > current_year for y in years_list) if years_list else False,
        })

    for income in recent_donations:
        recent_transactions.append({
            "type": "income",
            "amount": income.amount,
            "description": income.reason,
            "reason": income.reason,
            "created_at": income.created_at,
            "income_type": income.income_type,
            "income_object": income,
            "member": income.member,
            "created_by": income.created_by,
            "paid_by": income.paid_by,
        })

    for expense in recent_expenses:
        recent_transactions.append({
            "type": "expense",
            "amount": expense.amount,
            "description": expense.description,
            "reason": expense.description,
            "created_at": expense.created_at,
            "category": expense.category,
            "expense_object": expense,
            "created_by": expense.created_by,
        })

    # ─── RECENT PROJECT DONATIONS (includes outside donors) ───
    recent_project_donations = ProjectDonation.objects.filter(
        status="CONFIRMED"
    ).select_related("project", "member", "outside_donor", "invited_by").order_by("-donation_date")[:5]

    for pd in recent_project_donations:
        donation_dt = pd.donation_date
        if isinstance(donation_dt, date) and not isinstance(donation_dt, datetime):
            donation_dt = datetime.combine(donation_dt, datetime.min.time())
        if donation_dt.tzinfo is None:
            donation_dt = timezone.make_aware(donation_dt)

        donor_name = (
            pd.member.full_name if pd.member
            else pd.outside_donor.full_name if pd.outside_donor
            else "Anonymous"
        )

        recent_transactions.append({
            "type": "project_donation",
            "amount": pd.amount,
            "description": f"Project Donation — {pd.project.title if pd.project else 'General'}",
            "reason": pd.narration or "Project Donation",
            "created_at": donation_dt,
            "donation_date": pd.donation_date,
            "project": pd.project,
            "donor_name": donor_name,
            "donor_type": pd.get_donor_type_display(),
            "outside_donor": pd.outside_donor,
            "member": pd.member,
            "invited_by": pd.invited_by,
            "reference_number": pd.reference_number,
        })

    recent_transactions.sort(key=lambda x: x["created_at"], reverse=True)
    recent_transactions = recent_transactions[:5]


    # Only include actual members in debtor list — Admins don't pay dues;
    # Executives are still members and remain included.
    members = exclude_admin_users(
        User.objects.filter(
            is_active=True,
            serial_number__isnull=False
        ).exclude(
            serial_number=""
        )
    )

    debtor_list = []
    for member in members:
        debt = DuesPayment.get_member_debt(member)
        if debt["debt_owed"] > 0:
            debtor_list.append({
                "member": member,
                "debt": debt["debt_owed"],
                "years_missed": len(debt["years_expected"]) - len(debt["years_paid"]),
            })

    debtor_list.sort(key=lambda x: x["debt"], reverse=True)
    top_debtors = debtor_list[:5]

    # Additional stats for dashboard
    partial_payments = DuesPayment.objects.filter(
        amount_paid__gt=0,
        amount_paid__lt=YEARLY_DUES,
    ).count()

    prepaid_count = DuesPayment.objects.filter(
        year__gt=current_year,
        amount_paid__gte=YEARLY_DUES,
    ).count()

    # ─── PROJECT DONATIONS ───
    # total_project_donations already calculated above

    total_member_project_donations = ProjectDonation.objects.filter(
        status="CONFIRMED", donor_type="MEMBER"
    ).aggregate(
        total=Coalesce(Sum("amount"), Value(0, output_field=DecimalField()))
    )["total"] or Decimal("0")

    total_outside_project_donations = ProjectDonation.objects.filter(
        status="CONFIRMED", donor_type="OUTSIDE"
    ).aggregate(
        total=Coalesce(Sum("amount"), Value(0, output_field=DecimalField()))
    )["total"] or Decimal("0")

    donations_by_project = ProjectDonation.objects.filter(
        status="CONFIRMED"
    ).values("project__title").annotate(
        total=Sum("amount"), count=Count("id")
    ).order_by("-total")

    highest_fundraising_project = donations_by_project.first()

    total_outside_donors_count = OutsideDonor.objects.count()

    total_raised_through_invitees = ProjectDonation.objects.filter(
        status="CONFIRMED", invited_by__isnull=False
    ).aggregate(
        total=Coalesce(Sum("amount"), Value(0, output_field=DecimalField()))
    )["total"] or Decimal("0")

    context = {
        "treasury_balance": treasury_balance,
        "total_income": total_income,
        "total_dues": total_dues,
        "total_donations": total_donations,
        "total_expenses": total_expenses,
        "total_project_donations": total_project_donations,
        "total_member_project_donations": total_member_project_donations,
        "total_outside_project_donations": total_outside_project_donations,
        "donations_by_project": list(donations_by_project),
        "highest_fundraising_project": highest_fundraising_project,
        "total_outside_donors_count": total_outside_donors_count,
        "total_raised_through_invitees": total_raised_through_invitees,
        "total_transactions": Income.objects.count() + Expense.objects.count(),
        "expenses_by_category": expenses_by_category,
        "recent_transactions": recent_transactions,
        "active_members": active_members,
        "dues_collection_rate": dues_collection_rate,
        "this_year_dues_paid": this_year_dues_paid,
        "this_year_dues_rate": this_year_dues_rate,
        "top_debtors": top_debtors,
        "current_year": current_year,
        "partial_payments": partial_payments,
        "prepaid_count": prepaid_count,
        "total_prepaid": total_prepaid,
    }
    return render(request, "finance/finance_summary.html", context)



# ============================================================
# AJAX ENDPOINTS
# ============================================================

@login_required
def search_members(request):
    """AJAX endpoint for member name auto-suggest."""
    q = request.GET.get("q", "").strip()
    if len(q) < 2:
        return JsonResponse({"results": []})

    users = User.objects.filter(
        Q(full_name__icontains=q) |
        Q(serial_number__icontains=q) |
        Q(phone__icontains=q)
    ).filter(
        serial_number__isnull=False
    ).exclude(
        serial_number=""
    )
    users = exclude_admin_users(users).distinct()[:10]

    results = []
    for u in users:
        html = (
            f'<div class="search-result-item">'
            f'<div class="search-result-name">{u.get_full_name()}</div>'
            f'<div class="search-result-meta">{u.serial_number} · {u.get_role_display()}</div>'
            f'</div>'
        )
        results.append({
            "id": u.id,
            "text": f"{u.get_full_name()} ({u.serial_number})",
            "html": html,
            "name": u.full_name,
            "serial": u.serial_number,
            "role": u.get_role_display(),
        })

    return JsonResponse({"results": results})


@login_required
def member_dues_preview(request):
    """AJAX endpoint for dues allocation preview."""
    member_id = request.GET.get("member_id")
    if not member_id:
        return JsonResponse({"outstanding": []})

    try:
        member = User.objects.get(pk=member_id)
    except User.DoesNotExist:
        return JsonResponse({"outstanding": []})

    outstanding = DuesPayment.get_outstanding_years(member)
    data = []
    for item in outstanding:
        data.append({
            "year": item["year"],
            "amount_paid": float(item["amount_paid"]),
            "remaining_balance": float(item["remaining_balance"]),
            "status": item["status"],
        })

    return JsonResponse({"outstanding": data})

# ============================================================
# PREPAID DUES
# ============================================================

@login_required
def prepaid_list(request):
    """List all members with prepaid dues (future years fully paid) — grouped by member."""
    current_year = timezone.now().year

    # Get all prepaid dues payments (year > current_year, fully paid)
    prepaid_members_qs = DuesPayment.objects.filter(
        year__gt=current_year,
        amount_paid__gte=YEARLY_DUES,
    ).select_related("member", "recorded_by").order_by("member__full_name", "-year")

    # Group by member: collect years and total amounts
    member_prepaid_map = {}
    for dp in prepaid_members_qs:
        member_id = dp.member_id
        if member_id not in member_prepaid_map:
            member_prepaid_map[member_id] = {
                "member": dp.member,
                "years": [],
                "total_amount": Decimal("0"),
                "latest_recorded_by": dp.recorded_by,
                "latest_date": dp.created_at,
            }
        member_prepaid_map[member_id]["years"].append(dp.year)
        member_prepaid_map[member_id]["total_amount"] += dp.amount_paid
        if dp.created_at > member_prepaid_map[member_id]["latest_date"]:
            member_prepaid_map[member_id]["latest_date"] = dp.created_at
            member_prepaid_map[member_id]["latest_recorded_by"] = dp.recorded_by

    # Build grouped records list
    prepaid_grouped = []
    for member_id, data in member_prepaid_map.items():
        years_sorted = sorted(data["years"])
        if len(years_sorted) == 1:
            year_display = str(years_sorted[0])
        else:
            year_display = f"{years_sorted[0]}–{years_sorted[-1]}"

        prepaid_grouped.append({
            "member": data["member"],
            "years": years_sorted,
            "year_display": year_display,
            "total_amount": data["total_amount"],
            "recorded_by": data["latest_recorded_by"],
            "created_at": data["latest_date"],
            "year_count": len(years_sorted),
        })

    # Sort by total amount (highest first)
    prepaid_grouped.sort(key=lambda x: x["total_amount"], reverse=True)

    # Calculate totals
    total_prepaid_amount = sum(item["total_amount"] for item in prepaid_grouped)
    total_prepaid_records = len(prepaid_grouped)
    prepaid_members_count = len(prepaid_grouped)

    # Get unique future years covered
    all_years = set()
    for item in prepaid_grouped:
        all_years.update(item["years"])
    years_with_prepaid = sorted(all_years, reverse=True)

    context = {
        "prepaid_records": prepaid_grouped,
        "total_prepaid_amount": total_prepaid_amount,
        "total_prepaid_records": total_prepaid_records,
        "prepaid_members_count": prepaid_members_count,
        "years_with_prepaid": years_with_prepaid,
        "current_year": current_year,
        "yearly_dues": YEARLY_DUES,
    }
    return render(request, "finance/prepaid_list.html", context)



@login_required
def prepaid_detail(request, member_id):
    """Show prepaid dues details for a specific member."""
    member = get_object_or_404(User, pk=member_id)
    current_year = timezone.now().year

    # Get all prepaid records for this member
    prepaid_records = DuesPayment.objects.filter(
        member=member,
        year__gt=current_year,
    ).select_related("recorded_by", "income").order_by("-year")

    # Calculate total prepaid
    total_prepaid = prepaid_records.aggregate(
        total=Sum("amount_paid")
    )["total"] or Decimal("0")

    # Get member's debt info for context
    debt_info = DuesPayment.get_member_debt(member)

    context = {
        "member": member,
        "prepaid_records": prepaid_records,
        "total_prepaid": total_prepaid,
        "debt_info": debt_info,
        "current_year": current_year,
        "yearly_dues": YEARLY_DUES,
    }
    return render(request, "finance/prepaid_detail.html", context)

# ============================================================
# YEARLY DUES DEBTORS (Feature 10, 11)
# ============================================================

@login_required
def dues_debtors_list(request):
    """
    Yearly Dues Debtors report: aggregated by member.
    Shows each member's total outstanding debt across all years,
    sorted by highest debtor first. Supports search and year filter.
    """
    current_year = timezone.now().year

    search_term = request.GET.get("search", "").strip()
    year_filter = request.GET.get("year", "")

    members_qs = User.objects.filter(
        serial_number__isnull=False
    ).exclude(serial_number="")
    members_qs = exclude_admin_users(members_qs)

    if search_term:
        members_qs = members_qs.filter(
            Q(full_name__icontains=search_term) |
            Q(serial_number__icontains=search_term) |
            Q(phone__icontains=search_term)
        )

    debtor_list = []
    for member in members_qs:
        debt_info = DuesPayment.get_member_debt(member)
        debt_owed = debt_info.get("debt_owed", Decimal("0"))

        if debt_owed <= 0:
            continue

        # If year filter is applied, only show members who owe for that year
        if year_filter:
            year_int = int(year_filter)
            join_year = DuesPayment.get_member_join_year(member)
            if year_int < join_year or year_int > current_year:
                continue
            dp = DuesPayment.objects.filter(member=member, year=year_int).first()
            if dp and dp.is_fully_paid:
                continue

        years_expected = debt_info.get("years_expected", [])
        years_paid = debt_info.get("years_paid", [])
        years_missed = len(years_expected) - len(years_paid)

        total_due = len(years_expected) * DuesPayment.YEARLY_DUES_AMOUNT
        total_paid = total_due - debt_owed

        # Get last payment date
        last_payment = DuesPaymentTransaction.objects.filter(
            member=member
        ).aggregate(max_date=Max("payment_date"))["max_date"]

        debtor_list.append({
            "member": member,
            "total_due": total_due,
            "total_paid": total_paid,
            "debt": debt_owed,
            "years_missed": years_missed,
            "years_expected": years_expected,
            "years_paid": years_paid,
            "last_payment_date": last_payment,
        })

    # Sort by highest debt first
    debtor_list.sort(key=lambda x: x["debt"], reverse=True)

    total_outstanding = sum(d["debt"] for d in debtor_list)
    total_debtor_members = len(debtor_list)

    paginator = Paginator(debtor_list, 25)
    page_obj = paginator.get_page(request.GET.get("page", 1))

    context = {
        "debtors": page_obj,
        "search_term": search_term,
        "year_filter": year_filter,
        "years": list(range(PLATFORM_START_YEAR, current_year + 1)),
        "stats": {
            "total_records": len(debtor_list),
            "total_members": total_debtor_members,
            "total_outstanding": total_outstanding,
        },
    }
    return render(request, "finance/dues_debtors_list.html", context)