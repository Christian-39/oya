"""
Views for OYA executives.
"""
import logging
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from auditlogs.services import log_action
from .models import Executive
from .forms import ExecutiveForm

logger = logging.getLogger("oya")


@login_required
def executive_list(request):
    """List all executives with search and filter."""
    queryset = Executive.objects.select_related("member").all()

    # Search
    search_term = request.GET.get("search", "")
    if search_term:
        queryset = queryset.filter(
            Q(member__full_name__icontains=search_term) |
            Q(member__serial_number__icontains=search_term) |
            Q(post__icontains=search_term)
        )

    # Status filter
    status_filter = request.GET.get("status", "")
    if status_filter == "current":
        queryset = queryset.filter(is_current=True)
    elif status_filter == "past":
        queryset = queryset.filter(is_current=False)

    # Ordering
    queryset = queryset.order_by("-is_current", "-start_date")

    paginator = Paginator(queryset, 25)
    page = request.GET.get("page", 1)
    executives = paginator.get_page(page)

    # Statistics
    total_executives = Executive.objects.count()
    current_count = Executive.objects.filter(is_current=True).count()

    # Current executives for org chart (separate queryset to avoid pagination issues)
    current_executives = Executive.objects.filter(is_current=True).select_related("member").order_by("post")

    context = {
        "executives": executives,
        "current_executives": current_executives,
        "search_term": search_term,
        "status_filter": status_filter,
        "total_executives": total_executives,
        "current_count": current_count,
        "post_choices": Executive.POST_CHOICES,
    }
    return render(request, "executives/executive_list.html", context)


@login_required
def executive_detail(request, pk):
    """Display executive details with manifesto from latest candidacy."""
    executive = get_object_or_404(
        Executive.objects.select_related("member"), pk=pk
    )
    
    # Get the member's latest manifesto from their candidacies
    latest_candidacy = executive.member.candidacies.select_related("election").order_by("-created_at").first()
    manifesto = latest_candidacy.manifesto if latest_candidacy else None
    manifesto_election = latest_candidacy.election if latest_candidacy else None
    
    # Get handover records for this executive
    handovers = executive.handovers.select_related("election").order_by("-created_at")
    
    return render(request, "executives/executive_detail.html", {
        "executive": executive,
        "manifesto": manifesto,
        "manifesto_election": manifesto_election,
        "handovers": handovers,
    })


@login_required
def executive_create(request):
    """Create a new executive."""
    if not request.user.has_executive_access():
        messages.error(request, "Executive access required.")
        return redirect("executives:executive_list")

    # Get members who are not currently assigned as executives
    from members.models import Member
    assigned_member_ids = Executive.objects.filter(is_current=True).values_list("member_id", flat=True)
    available_members = Member.objects.filter(
        status="ACTIVE"
    ).exclude(
        id__in=assigned_member_ids
    ).order_by("full_name")

    if request.method == "POST":
        form = ExecutiveForm(request.POST)
        if form.is_valid():
            executive = form.save()
            log_action(
                user=request.user,
                action="CREATE",
                object_type="Executive",
                object_id=executive.id,
                ip_address=getattr(request, "client_ip", ""),
                description=f"Assigned {executive.post} to {executive.member.full_name}"
            )
            messages.success(
                request,
                f"{executive.post} assigned to {executive.member.full_name}."
            )
            return redirect("executives:executive_list")
        else:
            for error in form.errors.values():
                messages.error(request, error)
    else:
        form = ExecutiveForm()

    context = {
        "form": form,
        "available_members": available_members,
        "post_choices": Executive.POST_CHOICES,
        "title": "Assign Executive Post",
        "action": "Assign"
    }
    return render(request, "executives/executive_form.html", context)


@login_required
def executive_update(request, pk):
    """Update an executive record."""
    if not request.user.has_executive_access():
        messages.error(request, "Executive access required.")
        return redirect("executives:executive_list")

    executive = get_object_or_404(Executive, pk=pk)

    # Get available members (exclude current executives except this one)
    from members.models import Member
    assigned_member_ids = Executive.objects.filter(is_current=True).exclude(pk=pk).values_list("member_id", flat=True)
    available_members = Member.objects.filter(
        status="ACTIVE"
    ).exclude(
        id__in=assigned_member_ids
    ).order_by("full_name")

    # Include the current member in available options
    if executive.member_id not in [m.id for m in available_members]:
        available_members = Member.objects.filter(
            Q(id=executive.member_id) | Q(id__in=[m.id for m in available_members])
        ).order_by("full_name")

    if request.method == "POST":
        form = ExecutiveForm(request.POST, instance=executive)
        if form.is_valid():
            form.save()
            log_action(
                user=request.user,
                action="UPDATE",
                object_type="Executive",
                object_id=executive.id,
                ip_address=getattr(request, "client_ip", ""),
                description=f"Updated {executive.post} for {executive.member.full_name}"
            )
            messages.success(request, "Executive record updated successfully.")
            return redirect("executives:executive_list")
        else:
            for error in form.errors.values():
                messages.error(request, error)
    else:
        form = ExecutiveForm(instance=executive)

    context = {
        "form": form,
        "available_members": available_members,
        "post_choices": Executive.POST_CHOICES,
        "title": "Update Executive",
        "action": "Update",
        "executive": executive
    }
    return render(request, "executives/executive_form.html", context)


@login_required
def executive_end_tenure(request, pk):
    """End an executive's tenure."""
    if not request.user.has_executive_access():
        messages.error(request, "Executive access required.")
        return redirect("executives:executive_list")

    executive = get_object_or_404(Executive, pk=pk)

    if request.method == "POST":
        from django.utils import timezone
        executive.end_date = timezone.now().date()
        executive.is_current = False
        executive.save()

        log_action(
            user=request.user,
            action="UPDATE",
            object_type="Executive",
            object_id=executive.id,
            ip_address=getattr(request, "client_ip", ""),
            description=f"Ended tenure for {executive.post} - {executive.member.full_name}"
        )
        messages.success(
            request,
            f"Tenure ended for {executive.member.full_name} as {executive.post}."
        )
        return redirect("executives:executive_list")

    return render(request, "executives/executive_end_tenure.html", {"executive": executive})
