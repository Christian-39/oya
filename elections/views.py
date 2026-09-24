"""
Views for OYA elections.
"""
import logging
from dashboard.services import invalidate_dashboard_cache
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q, Sum
from decimal import Decimal
from django.db import transaction
from django.db.utils import OperationalError
from auditlogs.services import log_action
from .models import Election, Candidate, HandoverLedger, Vote
from .forms import ElectionForm, CandidateForm, HandoverLedgerForm

logger = logging.getLogger("oya")


@login_required
def election_list(request):
    """List all elections with search and filter."""
    queryset = Election.objects.all()

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
    elections = paginator.get_page(page)

    context = {
        "elections": elections,
        "search_term": search_term,
        "status_filter": status_filter,
        "status_choices": Election.STATUS_CHOICES,
    }
    return render(request, "elections/election_list.html", context)


@login_required
def election_detail(request, pk):
    """Display election details with candidates."""
    election = get_object_or_404(Election.objects.prefetch_related("candidates"), pk=pk)
    candidates = election.candidates.select_related("member").all()

    # Determine which posts the current user has already voted for in this election
    voted_posts = set()
    if request.user.is_authenticated:
        try:
            voted_posts = set(
                Vote.objects.filter(
                    voter=request.user, election=election
                ).values_list("post", flat=True)
            )
        except OperationalError:
            # Vote table may not exist yet (migration pending)
            pass

    context = {
        "election": election,
        "candidates": candidates,
        "voted_posts": voted_posts,
    }
    return render(request, "elections/election_detail.html", context)


@login_required
def election_create(request):
    """Create a new election."""
    if not request.user.has_executive_access():
        messages.error(request, "Executive access required.")
        return redirect("elections:election_list")

    if request.method == "POST":
        form = ElectionForm(request.POST)
        if form.is_valid():
            election = form.save()
            log_action(
                user=request.user,
                action="CREATE",
                object_type="Election",
                object_id=election.id,
                ip_address=getattr(request, "client_ip", ""),
                description=f"Created election: {election.title}"
            )
            messages.success(request, f"Election '{election.title}' created successfully.")
            invalidate_dashboard_cache()
            return redirect("elections:election_list")
        else:
            for error in form.errors.values():
                messages.error(request, error)
    else:
        form = ElectionForm()

    return render(request, "elections/election_form.html", {
        "form": form,
        "title": "Create Election",
        "action": "Create"
    })


@login_required
def election_update(request, pk):
    """Update an election."""
    if not request.user.has_executive_access():
        messages.error(request, "Executive access required.")
        return redirect("elections:election_list")

    election = get_object_or_404(Election, pk=pk)

    if request.method == "POST":
        form = ElectionForm(request.POST, instance=election)
        if form.is_valid():
            form.save()
            log_action(
                user=request.user,
                action="UPDATE",
                object_type="Election",
                object_id=election.id,
                ip_address=getattr(request, "client_ip", ""),
                description=f"Updated election: {election.title}"
            )
            messages.success(request, "Election updated successfully.")
            invalidate_dashboard_cache()
            return redirect("elections:election_list")
        else:
            for error in form.errors.values():
                messages.error(request, error)
    else:
        form = ElectionForm(instance=election)

    # FIX: Render the form on GET, only redirect after successful POST
    return render(request, "elections/election_form.html", {
        "form": form,
        "title": "Update Election",
        "action": "Update",
        "election": election
    })
    

@login_required
def candidate_create(request):
    """Add a candidate to an election."""
    if not request.user.has_executive_access():
        messages.error(request, "Executive access required.")
        return redirect("elections:election_list")

    election_id = request.GET.get("election")
    if request.method == "POST":
        form = CandidateForm(request.POST, request.FILES)
        if form.is_valid():
            candidate = form.save()
            log_action(
                user=request.user,
                action="CREATE",
                object_type="Candidate",
                object_id=candidate.id,
                ip_address=getattr(request, "client_ip", ""),
                description=f"Added candidate {candidate.member.full_name} for {candidate.post}"
            )
            messages.success(
                request,
                f"{candidate.member.full_name} added as candidate for {candidate.post}."
            )
            invalidate_dashboard_cache()
            return redirect("elections:election_detail", pk=candidate.election.id)
        else:
            for error in form.errors.values():
                messages.error(request, error)
    else:
        initial = {}
        if election_id:
            initial["election"] = election_id
        form = CandidateForm(initial=initial)

    return render(request, "elections/candidate_form.html", {
        "form": form,
        "title": "Add Candidate",
        "action": "Add"
    })


@login_required
def candidate_update(request, pk):
    """Update a candidate's information."""
    if not request.user.has_executive_access():
        messages.error(request, "Executive access required.")
        return redirect("elections:election_list")

    candidate = get_object_or_404(Candidate, pk=pk)

    if request.method == "POST":
        form = CandidateForm(request.POST, request.FILES, instance=candidate)
        if form.is_valid():
            candidate = form.save()
            log_action(
                user=request.user,
                action="UPDATE",
                object_type="Candidate",
                object_id=candidate.id,
                ip_address=getattr(request, "client_ip", ""),
                description=f"Updated candidate {candidate.member.full_name} for {candidate.post}"
            )
            messages.success(
                request,
                f"Candidate {candidate.member.full_name} updated successfully."
            )
            invalidate_dashboard_cache()
            return redirect("elections:election_detail", pk=candidate.election.id)
        else:
            for error in form.errors.values():
                messages.error(request, error)
    else:
        form = CandidateForm(instance=candidate)

    return render(request, "elections/candidate_form.html", {
        "form": form,
        "candidate": candidate,
        "title": "Edit Candidate",
        "action": "Update"
    })


@login_required
def cast_vote(request, pk):
    """Cast a vote for a candidate."""
    if request.method != "POST":
        messages.error(request, "Invalid request method.")
        return redirect("elections:election_list")

    candidate = get_object_or_404(
        Candidate.objects.select_related("election", "member"), pk=pk
    )
    election = candidate.election

    if election.status != "ONGOING":
        messages.error(request, "Voting is only allowed for ongoing elections.")
        return redirect("elections:election_detail", pk=election.id)

    # Prevent voting for the same post twice in the same election
    try:
        already_voted = Vote.objects.filter(
            voter=request.user, election=election, post=candidate.post
        ).exists()
    except OperationalError:
        messages.error(request, "Voting system is temporarily unavailable. Please try again later.")
        return redirect("elections:election_detail", pk=election.id)

    if already_voted:
        messages.warning(
            request,
            f"You have already voted for {candidate.post} in this election."
        )
        return redirect("elections:election_detail", pk=election.id)

    with transaction.atomic():
        Vote.objects.create(
            voter=request.user,
            election=election,
            candidate=candidate,
            post=candidate.post,
        )
        candidate.votes += 1
        candidate.save(update_fields=["votes"])

    log_action(
        user=request.user,
        action="VOTE",
        object_type="Candidate",
        object_id=candidate.id,
        ip_address=getattr(request, "client_ip", ""),
        description=f"Voted for {candidate.member.full_name} ({candidate.post}) in {election.title}"
    )
    messages.success(
        request,
        f"Vote cast for {candidate.member.full_name} for {candidate.post}."
    )
    invalidate_dashboard_cache()
    return redirect("elections:election_detail", pk=election.id)


# ============================================================
# HANDOVER LEDGER VIEWS
# ============================================================

@login_required
def handover_list(request):
    """List all handover ledgers with search and pagination."""
    queryset = HandoverLedger.objects.select_related("executive__member", "election").all()

    search_term = request.GET.get("search", "")
    if search_term:
        queryset = queryset.filter(
            Q(executive__member__full_name__icontains=search_term) |
            Q(executive__post__icontains=search_term) |
            Q(election__title__icontains=search_term)
        )

    paginator = Paginator(queryset, 12)
    page = request.GET.get("page", 1)
    handovers = paginator.get_page(page)

    # Summary stats — plain Sum, then fall back to Decimal("0") in Python
    agg = HandoverLedger.objects.aggregate(
        total_cash_remaining=Sum("cash_remaining"),
        sum_income=Sum("total_income"),
        sum_dues=Sum("total_dues"),
        sum_donations=Sum("total_donations"),
        sum_taskforce=Sum("taskforce_revenue"),
    )

    stats = {
        "total": HandoverLedger.objects.count(),
        "total_cash_remaining": agg["total_cash_remaining"] or Decimal("0"),
        "total_revenue": (
            (agg["sum_income"] or Decimal("0")) +
            (agg["sum_dues"] or Decimal("0")) +
            (agg["sum_donations"] or Decimal("0")) +
            (agg["sum_taskforce"] or Decimal("0"))
        ),
    }

    return render(request, "elections/handover_list.html", {
        "handovers": handovers,
        "search_term": search_term,
        "stats": stats,
    })


@login_required
def handover_detail(request, pk):
    """Display comprehensive handover details. Tenure-scoped data (cases,
    finance) is fetched via elections.administrations — the same
    calculation engine that powers the Executive Handover Report and
    HandoverLedger.recalculate_aggregates() — so this page, the ledger's
    own stored figures, and the full report always agree and nothing is
    queried twice."""
    from django.db.models import Sum, Count
    from elections.administrations import (
        _cases_section, _taskforce_section, _motorcycles_section, _finance_section,
    )

    handover = get_object_or_404(
        HandoverLedger.objects.select_related("executive__member", "election"),
        pk=pk
    )

    from projects.models import Project
    from project_donations.models import Donation as ProjectDonation
    from operations.models import CaseFile, TaskForceMember, Motorcycle

    start = handover.tenure_start
    end = handover.tenure_end

    if start and end:
        cases_data = _cases_section(start, end, limit=50)
        taskforce_data = _taskforce_section(start, end, limit=50)
        motorcycles_data = _motorcycles_section(start, end, limit=50)
        finance_data = _finance_section(start, end)
        cases = cases_data["handled"]
        taskforce_members = taskforce_data["all_current"]
        motorcycles = motorcycles_data["all_motorcycles"]
        recent_income = finance_data["recent_income"][:10]
        recent_expenses = finance_data["recent_expenses"][:10]
        recent_dues = finance_data["recent_dues"][:10]
    else:
        # No resolvable tenure window (shouldn't happen for a saved ledger,
        # since recalculate_aggregates() always derives one from the
        # executive record) — degrade to empty rather than showing
        # unrelated, unscoped data.
        cases = CaseFile.objects.none()
        taskforce_members = TaskForceMember.objects.none()
        motorcycles = Motorcycle.objects.none()
        recent_income = recent_expenses = recent_dues = []

    # ONE query: per-project donation totals/counts within the tenure window.
    if start and end:
        donation_stats = (
            ProjectDonation.objects.filter(
                status="CONFIRMED", donation_date__range=(start, end)
            )
            .values("project_id")
            .annotate(total=Sum("amount"), count=Count("id"))
        )
    else:
        donation_stats = ProjectDonation.objects.none()
    stats_by_project = {row["project_id"]: row for row in donation_stats}

    # ONE query: top 5 donations per project only for projects that had donations.
    project_ids_with_donations = list(stats_by_project.keys())
    donations_qs = ProjectDonation.objects.filter(
        project_id__in=project_ids_with_donations,
        status="CONFIRMED",
        donation_date__range=(start, end),
    ).select_related("member", "outside_donor").order_by("project_id", "-donation_date") if (start and end) else ProjectDonation.objects.none()

    donations_by_project = {}
    for d in donations_qs:
        donations_by_project.setdefault(d.project_id, []).append(d)

    # Cap unbounded project list
    projects = Project.objects.all().order_by("-created_at")[:100]
    projects_with_donations = []
    for project in projects:
        stats = stats_by_project.get(project.id, {"total": 0, "count": 0})
        projects_with_donations.append({
            "project": project,
            "donations": donations_by_project.get(project.id, [])[:5],
            "donation_total": stats["total"] or 0,
            "donation_count": stats["count"],
        })

    context = {
        "handover": handover,
        "taskforce_members": taskforce_members,
        "motorcycles": motorcycles,
        "cases": cases,
        "recent_income": recent_income,
        "recent_expenses": recent_expenses,
        "recent_dues": recent_dues,
        "projects_with_donations": projects_with_donations,
    }
    return render(request, "elections/handover_detail.html", context)


@login_required
def handover_create(request):
    """Create a comprehensive handover ledger entry."""
    if not request.user.has_executive_access():
        messages.error(request, "Executive access required.")
        return redirect("elections:handover_list")

    if request.method == "POST":
        form = HandoverLedgerForm(request.POST, user=request.user)
        if form.is_valid():
            handover = form.save()
            log_action(
                user=request.user,
                action="CREATE",
                object_type="HandoverLedger",
                object_id=handover.id,
                ip_address=getattr(request, "client_ip", ""),
                description=f"Created handover ledger for {handover.executive} (₦{handover.net_financial_position:,.2f})"
            )
            messages.success(request, "Handover ledger created successfully with auto-calculated aggregates.")
            invalidate_dashboard_cache()
            return redirect("elections:handover_detail", pk=handover.id)
        else:
            for error in form.errors.values():
                messages.error(request, error)
    else:
        form = HandoverLedgerForm(user=request.user)

    return render(request, "elections/handover_form.html", {
        "form": form,
        "title": "Create Handover Ledger",
        "action": "Create"
    })


@login_required
def handover_update(request, pk):
    """Update a handover ledger and recalculate aggregates."""
    if not request.user.has_executive_access():
        messages.error(request, "Executive access required.")
        return redirect("elections:handover_list")

    handover = get_object_or_404(HandoverLedger, pk=pk)

    if request.method == "POST":
        form = HandoverLedgerForm(request.POST, instance=handover, user=request.user)
        if form.is_valid():
            handover = form.save()
            log_action(
                user=request.user,
                action="UPDATE",
                object_type="HandoverLedger",
                object_id=handover.id,
                ip_address=getattr(request, "client_ip", ""),
                description=f"Updated handover ledger for {handover.executive}"
            )
            messages.success(request, "Handover ledger updated and aggregates recalculated.")
            invalidate_dashboard_cache()
            return redirect("elections:handover_detail", pk=handover.id)
        else:
            for error in form.errors.values():
                messages.error(request, error)
    else:
        form = HandoverLedgerForm(instance=handover, user=request.user)

    return render(request, "elections/handover_form.html", {
        "form": form,
        "handover": handover,
        "title": "Edit Handover Ledger",
        "action": "Update"
    })


@login_required
def handover_delete(request, pk):
    """Delete a handover ledger."""
    if not request.user.has_admin_access():
        messages.error(request, "Admin access required.")
        return redirect("elections:handover_list")

    handover = get_object_or_404(HandoverLedger, pk=pk)

    if request.method == "POST":
        executive_name = str(handover.executive)
        handover.delete()
        log_action(
            user=request.user,
            action="DELETE",
            object_type="HandoverLedger",
            object_id=pk,
            ip_address=getattr(request, "client_ip", ""),
            description=f"Deleted handover ledger for {executive_name}"
        )
        messages.success(request, f"Handover ledger for {executive_name} deleted.")
        invalidate_dashboard_cache()
        return redirect("elections:handover_list")

    return render(request, "elections/handover_confirm_delete.html", {"handover": handover})


@login_required
def administration_list(request):
    """Previous Administrations page — every executive administration
    ordered by election, newest first, with a link into its full
    Executive Handover Report."""
    from .administrations import list_administrations

    administrations = list_administrations()
    return render(request, "elections/administration_list.html", {
        "administrations": administrations,
    })


@login_required
def administration_report(request, key):
    """The comprehensive, automatically generated Executive Handover
    Report for a single administration."""
    from .administrations import build_administration_report

    report = build_administration_report(key)
    if report is None:
        messages.error(request, "That administration could not be found.")
        return redirect("elections:administration_list")

    log_action(
        user=request.user,
        action="VIEW",
        object_type="ExecutiveHandoverReport",
        object_id=None,
        ip_address=getattr(request, "client_ip", ""),
        description=f"Viewed Executive Handover Report for {report['administration']['name']}"
    )

    return render(request, "elections/administration_report.html", {
        "report": report,
        "administration": report["administration"],
    })