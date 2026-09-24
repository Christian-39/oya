"""
Views for OYA Project Donations.
"""
import logging
from decimal import Decimal
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q, Sum, Count, Value, DecimalField
from django.db.models.functions import Coalesce
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_http_methods
from django.db import transaction
from django.utils import timezone
from auditlogs.services import log_action
from projects.models import Project
from settingsapp.models import DonationGroup, DonationGroupMembership
from .models import OutsideDonor, Donation, Pledge, PledgePayment
from .forms import OutsideDonorForm, DonationForm, PledgeForm, PledgePaymentForm
from .reports import (
    generate_project_fundraising_report,
    generate_donation_history_report,
    generate_member_donation_history_report,
    generate_outside_donor_statement,
)

logger = logging.getLogger("oya")


def _format_money(value):
    """Safely format a numeric value as Naira."""
    if value is None:
        return "N/A"
    return f"₦{value:,.2f}"


def _donation_log_description(donation, action_verb):
    """Build a crash-safe audit-log description for any donation type."""
    proj = donation.project.title if donation.project else "Unknown Project"

    # Build donor label manually (Donation has no get_donor_display)
    if donation.donor_type == "MEMBER" and donation.member:
        donor = donation.member.full_name
    elif donation.donor_type == "OUTSIDE" and donation.outside_donor:
        donor = donation.outside_donor.full_name
    else:
        donor = donation.get_donor_type_display() if hasattr(donation, "get_donor_type_display") else str(donation.donor_type)

    if donation.donation_type == "CASH":
        return f"{action_verb} donation: {_format_money(donation.amount)} from {donor} for {proj}"

    if donation.donation_type == "MATERIAL":
        est = _format_money(donation.estimated_value)
        return (
            f"{action_verb} material donation: {donation.material_name or 'N/A'} "
            f"(Qty: {donation.quantity or 'N/A'}, Est: {est}) from {donor} for {proj}"
        )

    if donation.donation_type == "LABOUR":
        days = f"{donation.number_of_days} day(s)" if donation.number_of_days else "N/A"
        return (
            f"{action_verb} labour donation: {donation.labour_type or 'N/A'} "
            f"({days}) from {donor} for {proj}"
        )

    # Fallback for any future types
    return f"{action_verb} donation: {_format_money(donation.amount)} from {donor} for {proj}"


# ============================================================
# OUTSIDE DONORS
# ============================================================

@login_required
def outside_donor_list(request):
    """List all outside donors with search and pagination."""
    queryset = OutsideDonor.objects.select_related("invited_by").all()

    search_term = request.GET.get("search", "")
    if search_term:
        queryset = queryset.filter(
            Q(full_name__icontains=search_term) |
            Q(phone_number__icontains=search_term) |
            Q(occupation__icontains=search_term) |
            Q(invited_by__full_name__icontains=search_term)
        )

    paginator = Paginator(queryset, 25)
    page = request.GET.get("page", 1)
    donors = paginator.get_page(page)

    stats = {
        "total": OutsideDonor.objects.count(),
        "total_donations": Donation.objects.filter(
            status="CONFIRMED", donor_type="OUTSIDE"
        ).aggregate(total=Coalesce(Sum("amount"), Value(0, output_field=DecimalField())))["total"],
    }

    context = {
        "donors": donors,
        "search_term": search_term,
        "stats": stats,
    }
    return render(request, "project_donations/outside_donor_list.html", context)


@login_required
def outside_donor_detail(request, pk):
    """Display complete outside donor profile."""
    donor = get_object_or_404(
        OutsideDonor.objects.select_related("invited_by"),
        pk=pk
    )
    donations = Donation.objects.filter(
        outside_donor=donor
    ).select_related("project", "recorded_by").order_by("-donation_date")

    context = {
        "donor": donor,
        "donations": donations,
        "total_donations": donor.total_donations,
        "donation_count": donor.donation_count,
        "projects_supported": donor.projects_supported,
    }
    return render(request, "project_donations/outside_donor_detail.html", context)


@login_required
def outside_donor_create(request):
    """Create a new outside donor."""
    if not request.user.has_executive_access():
        messages.error(request, "Executive access required.")
        return redirect("project_donations:outside_donor_list")

    if request.method == "POST":
        form = OutsideDonorForm(request.POST, request.FILES)
        if form.is_valid():
            donor = form.save()
            log_action(
                user=request.user,
                action="CREATE",
                object_type="OutsideDonor",
                object_id=donor.id,
                ip_address=getattr(request, "client_ip", ""),
                description=f"Created outside donor: {donor.full_name}"
            )
            messages.success(
                request,
                f"Outside donor '{donor.full_name}' created successfully."
            )
            return redirect("project_donations:outside_donor_list")
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field}: {error}")
    else:
        form = OutsideDonorForm()

    return render(request, "project_donations/outside_donor_form.html", {
        "form": form,
        "title": "Add Outside Donor",
        "action": "Create"
    })




@login_required
def outside_donor_update(request, pk):
    """Update an existing outside donor."""
    if not request.user.has_executive_access():
        messages.error(request, "Executive access required.")
        return redirect("project_donations:outside_donor_list")

    donor = get_object_or_404(OutsideDonor, pk=pk)

    if request.method == "POST":
        form = OutsideDonorForm(request.POST, request.FILES, instance=donor)
        if form.is_valid():
            donor = form.save()
            log_action(
                user=request.user,
                action="UPDATE",
                object_type="OutsideDonor",
                object_id=donor.id,
                ip_address=getattr(request, "client_ip", ""),
                description=f"Updated outside donor: {donor.full_name}"
            )
            messages.success(
                request,
                f"Outside donor '{donor.full_name}' updated successfully."
            )
            return redirect("project_donations:outside_donor_detail", pk=donor.pk)
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field}: {error}")
    else:
        form = OutsideDonorForm(instance=donor)

    return render(request, "project_donations/outside_donor_form.html", {
        "form": form,
        "donor": donor,
        "title": "Edit Outside Donor",
        "action": "Update"
    })



@login_required
def outside_donor_delete(request, pk):
    """Delete an outside donor (admin only)."""
    if not request.user.has_admin_access():
        messages.error(request, "Admin access required.")
        return redirect("project_donations:outside_donor_list")

    donor = get_object_or_404(OutsideDonor, pk=pk)

    if request.method == "POST":
        name = donor.full_name
        donor.delete()
        log_action(
            user=request.user,
            action="DELETE",
            object_type="OutsideDonor",
            object_id=pk,
            ip_address=getattr(request, "client_ip", ""),
            description=f"Deleted outside donor: {name}"
        )
        messages.success(request, f"Outside donor '{name}' deleted.")
        return redirect("project_donations:outside_donor_list")

    return render(
        request,
        "project_donations/outside_donor_confirm_delete.html",
        {"donor": donor}
    )


# ============================================================
# DONATIONS
# ============================================================

@login_required
def donation_list(request):
    """List all donations with search, filter, and pagination."""
    queryset = Donation.objects.select_related(
        "project", "member", "outside_donor", "recorded_by", "invited_by"
    ).all()

    search_term = request.GET.get("search", "")
    if search_term:
        queryset = queryset.filter(
            Q(project__title__icontains=search_term) |
            Q(member__full_name__icontains=search_term) |
            Q(outside_donor__full_name__icontains=search_term) |
            Q(invited_by__full_name__icontains=search_term) |
            Q(reference_number__icontains=search_term) |
            Q(narration__icontains=search_term)
        )

    project_filter = request.GET.get("project", "")
    if project_filter:
        queryset = queryset.filter(project_id=project_filter)

    donor_type_filter = request.GET.get("donor_type", "")
    if donor_type_filter:
        queryset = queryset.filter(donor_type=donor_type_filter)

    donation_type_filter = request.GET.get("donation_type", "")
    if donation_type_filter:
        queryset = queryset.filter(donation_type=donation_type_filter)

    group_filter = request.GET.get("group", "")
    if group_filter:
        member_ids = DonationGroupMembership.objects.filter(
            group_id=group_filter
        ).values_list("member_id", flat=True)
        queryset = queryset.filter(member_id__in=member_ids)

    amount_min = request.GET.get("amount_min", "")
    if amount_min:
        try:
            queryset = queryset.filter(amount__gte=Decimal(amount_min))
        except Exception:
            pass

    amount_max = request.GET.get("amount_max", "")
    if amount_max:
        try:
            queryset = queryset.filter(amount__lte=Decimal(amount_max))
        except Exception:
            pass

    date_from = request.GET.get("date_from", "")
    if date_from:
        queryset = queryset.filter(donation_date__gte=date_from)

    date_to = request.GET.get("date_to", "")
    if date_to:
        queryset = queryset.filter(donation_date__lte=date_to)

    status_filter = request.GET.get("status", "")
    if status_filter:
        queryset = queryset.filter(status=status_filter)

    paginator = Paginator(queryset, 25)
    page = request.GET.get("page", 1)
    donations = paginator.get_page(page)

    total_donations = Donation.objects.filter(status="CONFIRMED").aggregate(
        total=Coalesce(Sum("amount"), Value(0, output_field=DecimalField()))
    )["total"]

    member_total = Donation.objects.filter(
        status="CONFIRMED", donor_type="MEMBER"
    ).aggregate(
        total=Coalesce(Sum("amount"), Value(0, output_field=DecimalField()))
    )["total"]

    outside_total = Donation.objects.filter(
        status="CONFIRMED", donor_type="OUTSIDE"
    ).aggregate(
        total=Coalesce(Sum("amount"), Value(0, output_field=DecimalField()))
    )["total"]

    context = {
        "donations": donations,
        "search_term": search_term,
        "project_filter": project_filter,
        "donor_type_filter": donor_type_filter,
        "donation_type_filter": donation_type_filter,
        "group_filter": group_filter,
        "amount_min": amount_min,
        "amount_max": amount_max,
        "date_from": date_from,
        "date_to": date_to,
        "status_filter": status_filter,
        "donor_type_choices": Donation.DONOR_TYPE_CHOICES,
        "donation_type_choices": Donation.DONATION_TYPE_CHOICES,
        "status_choices": Donation.STATUS_CHOICES,
        "total_donations": total_donations,
        "member_total": member_total,
        "outside_total": outside_total,
        "fundraising_projects": Project.objects.filter(enable_fundraising=True).order_by("-created_at"),
        "donation_groups": DonationGroup.objects.filter(is_active=True).order_by("name"),
    }
    return render(request, "project_donations/donation_list.html", context)


@login_required
def donation_detail(request, pk):
    """Display donation details."""
    donation = get_object_or_404(
        Donation.objects.select_related(
            "project", "member", "outside_donor", "recorded_by", "invited_by"
        ),
        pk=pk
    )
    return render(request, "project_donations/donation_detail.html", {"donation": donation})


@login_required
def donation_create(request):
    """Record a new donation."""
    if not request.user.has_executive_access():
        messages.error(request, "Executive access required.")
        return redirect("project_donations:donation_list")

    if request.method == "POST":
        form = DonationForm(request.POST)
        if form.is_valid():
            donation = form.save(commit=False)
            donation.recorded_by = request.user
            donation.save()
            log_action(
                user=request.user,
                action="CREATE",
                object_type="Donation",
                object_id=donation.id,
                ip_address=getattr(request, "client_ip", ""),
                description=_donation_log_description(donation, "Recorded"),
            )
            messages.success(request, "Donation recorded successfully.")
            return redirect("project_donations:donation_list")
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field}: {error}")
    else:
        form = DonationForm()

    return render(request, "project_donations/donation_form.html", {
        "form": form,
        "title": "Record Donation",
        "action": "Save"
    })


@login_required
def donation_update(request, pk):
    """Update an existing donation."""
    if not request.user.has_executive_access():
        messages.error(request, "Executive access required.")
        return redirect("project_donations:donation_list")

    donation = get_object_or_404(Donation, pk=pk)

    if request.method == "POST":
        form = DonationForm(request.POST, instance=donation)
        if form.is_valid():
            donation = form.save()
            log_action(
                user=request.user,
                action="UPDATE",
                object_type="Donation",
                object_id=donation.id,
                ip_address=getattr(request, "client_ip", ""),
                description=_donation_log_description(donation, "Updated"),
            )
            messages.success(request, "Donation updated successfully.")
            return redirect("project_donations:donation_list")
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field}: {error}")
    else:
        form = DonationForm(instance=donation)

    return render(request, "project_donations/donation_form.html", {
        "form": form,
        "donation": donation,
        "title": "Edit Donation",
        "action": "Update"
    })


@login_required
def donation_delete(request, pk):
    """Delete a donation (admin only)."""
    if not request.user.has_admin_access():
        messages.error(request, "Admin access required.")
        return redirect("project_donations:donation_list")

    donation = get_object_or_404(Donation, pk=pk)

    if request.method == "POST":
        desc = _donation_log_description(donation, "Deleted")
        donation.delete()
        log_action(
            user=request.user,
            action="DELETE",
            object_type="Donation",
            object_id=pk,
            ip_address=getattr(request, "client_ip", ""),
            description=desc,
        )
        messages.success(request, "Donation deleted.")
        return redirect("project_donations:donation_list")

    return render(
        request,
        "project_donations/donation_confirm_delete.html",
        {"donation": donation}
    )


@login_required
@require_http_methods(["POST"])
def donation_fulfill(request, pk):
    """Mark a Pledge-status donation as fulfilled. Confirming the donation
    also marks its linked Pledge record Completed automatically (via the
    sync_donation_pledge signal), and -- for Money/Material -- creates or
    updates the treasury Income record (via sync_donation_to_finance)."""
    if not request.user.has_executive_access():
        messages.error(request, "Executive access required.")
        return redirect("project_donations:donation_detail", pk=pk)

    donation = get_object_or_404(Donation, pk=pk)
    if donation.status != "PLEDGE":
        messages.error(request, "Only donations still at Pledge status can be fulfilled.")
        return redirect("project_donations:donation_detail", pk=pk)

    donation.status = "CONFIRMED"
    donation.save()
    log_action(
        user=request.user,
        action="UPDATE",
        object_type="Donation",
        object_id=donation.id,
        ip_address=getattr(request, "client_ip", ""),
        description=f"Marked pledge fulfilled: {donation.display_value} for {donation.project.title}"
    )
    messages.success(request, "Pledge marked as fulfilled -- donation confirmed and pledge completed.")
    return redirect("project_donations:donation_detail", pk=pk)


@login_required
@require_http_methods(["POST"])
def donation_cancel_pledge(request, pk):
    """Cancel a Pledge-status donation (the donor withdrew their commitment).
    Marks the linked Pledge Cancelled too, automatically."""
    if not request.user.has_executive_access():
        messages.error(request, "Executive access required.")
        return redirect("project_donations:donation_detail", pk=pk)

    donation = get_object_or_404(Donation, pk=pk)
    if donation.status != "PLEDGE":
        messages.error(request, "Only donations still at Pledge status can be cancelled this way.")
        return redirect("project_donations:donation_detail", pk=pk)

    donation.status = "CANCELLED"
    donation.save()
    log_action(
        user=request.user,
        action="UPDATE",
        object_type="Donation",
        object_id=donation.id,
        ip_address=getattr(request, "client_ip", ""),
        description=f"Cancelled pledge: {donation.display_value} for {donation.project.title}"
    )
    messages.success(request, "Pledge cancelled.")
    return redirect("project_donations:donation_detail", pk=pk)


# ============================================================
# REPORTS
# ============================================================

@login_required
def project_fundraising_report(request, project_id):
    """Generate PDF report for project fundraising summary."""
    if not request.user.has_executive_access():
        messages.error(request, "Executive access required.")
        return redirect("projects:project_detail", pk=project_id)

    from projects.models import Project
    project = get_object_or_404(Project, pk=project_id)

    pdf = generate_project_fundraising_report(project)
    response = HttpResponse(pdf, content_type="application/pdf")
    response["Content-Disposition"] = (
        f'attachment; filename="fundraising_report_{project.id}.pdf"'
    )
    return response


@login_required
def outside_donor_statement_pdf(request, pk):
    """Generate PDF statement for an outside donor."""
    if not request.user.has_executive_access():
        messages.error(request, "Executive access required.")
        return redirect("project_donations:outside_donor_detail", pk=pk)

    donor = get_object_or_404(OutsideDonor, pk=pk)
    pdf = generate_outside_donor_statement(donor)
    response = HttpResponse(pdf, content_type="application/pdf")
    response["Content-Disposition"] = (
        f'attachment; filename="outside_donor_statement_{pk}.pdf"'
    )
    return response


@login_required
def member_donation_history_pdf(request, pk):
    """Generate PDF report for member donation history."""
    if not request.user.has_executive_access():
        messages.error(request, "Executive access required.")
        return redirect("members:member_detail", pk=pk)

    from members.models import Member
    member = get_object_or_404(Member, pk=pk)
    pdf = generate_member_donation_history_report(member)
    response = HttpResponse(pdf, content_type="application/pdf")
    response["Content-Disposition"] = (
        f'attachment; filename="member_donation_history_{pk}.pdf"'
    )
    return response


@login_required
def donation_history_report(request):
    """Generate PDF report for all donation history."""
    if not request.user.has_executive_access():
        messages.error(request, "Executive access required.")
        return redirect("project_donations:donation_list")

    donations = Donation.objects.select_related(
        "project", "member", "outside_donor", "recorded_by"
    ).filter(status="CONFIRMED").order_by("-donation_date")

    pdf = generate_donation_history_report(donations)
    response = HttpResponse(pdf, content_type="application/pdf")
    response["Content-Disposition"] = 'attachment; filename="donation_history.pdf"'
    return response


# ============================================================
# AJAX ENDPOINTS
# ============================================================

@login_required
def search_outside_donors_ajax(request):
    """AJAX endpoint for outside donor auto-suggest."""
    search_term = request.GET.get("q", "").strip()
    if len(search_term) < 2:
        return JsonResponse({"results": []})

    donors = OutsideDonor.objects.filter(
        Q(full_name__icontains=search_term) |
        Q(phone_number__icontains=search_term)
    )[:10]

    results = [
        {
            "id": d.id,
            "text": f"{d.full_name} ({d.phone_number or 'No phone'})",
            "full_name": d.full_name,
            "phone": d.phone_number,
        }
        for d in donors
    ]

    return JsonResponse({"results": results})


@login_required
def get_outside_donor_inviter_ajax(request):
    """AJAX endpoint to get the default inviter for an outside donor."""
    donor_id = request.GET.get("donor_id", "")
    if not donor_id:
        return JsonResponse({"invited_by_id": None})

    try:
        donor = OutsideDonor.objects.get(pk=donor_id)
        return JsonResponse({
            "invited_by_id": donor.invited_by_id,
            "invited_by_name": donor.invited_by.full_name if donor.invited_by else ""
        })
    except OutsideDonor.DoesNotExist:
        return JsonResponse({"invited_by_id": None})


# ============================================================
# PLEDGES (Feature 6, 7, 9)
# ============================================================

@login_required
def pledge_list(request):
    """List all pledges with search, filter (status/overdue), and pagination (Feature 9)."""
    queryset = Pledge.objects.select_related("member", "outside_donor", "project", "created_by").all()

    search_term = request.GET.get("search", "")
    if search_term:
        queryset = queryset.filter(
            Q(member__full_name__icontains=search_term) |
            Q(member__serial_number__icontains=search_term) |
            Q(outside_donor__full_name__icontains=search_term) |
            Q(project__title__icontains=search_term)
        )

    donation_type_filter = request.GET.get("donation_type", "")
    if donation_type_filter:
        queryset = queryset.filter(donation_type=donation_type_filter)

    status_filter = request.GET.get("status", "")
    if status_filter == "OVERDUE":
        queryset = queryset.filter(
            due_date__lt=timezone.now().date()
        ).exclude(status__in=["COMPLETED", "CANCELLED"])
    elif status_filter:
        queryset = queryset.filter(status=status_filter)

    project_filter = request.GET.get("project", "")
    if project_filter:
        queryset = queryset.filter(project_id=project_filter)

    paginator = Paginator(queryset, 25)
    page = request.GET.get("page", 1)
    pledges = paginator.get_page(page)

    all_pledges = Pledge.objects.exclude(status="CANCELLED")
    total_pledged = all_pledges.aggregate(
        total=Coalesce(Sum("pledged_amount"), Value(0, output_field=DecimalField()))
    )["total"]
    total_outstanding = sum((p.outstanding_balance for p in all_pledges), Decimal("0"))

    context = {
        "pledges": pledges,
        "search_term": search_term,
        "status_filter": status_filter,
        "project_filter": project_filter,
        "donation_type_filter": donation_type_filter,
        "status_choices": Pledge.STATUS_CHOICES,
        "donation_type_choices": Donation.DONATION_TYPE_CHOICES,
        "stats": {
            "total": Pledge.objects.count(),
            "pending": Pledge.objects.filter(status="PENDING").count(),
            "partially_paid": Pledge.objects.filter(status="PARTIALLY_PAID").count(),
            "completed": Pledge.objects.filter(status="COMPLETED").count(),
            "cancelled": Pledge.objects.filter(status="CANCELLED").count(),
            "total_pledged": total_pledged,
            "total_outstanding": total_outstanding,
        },
        "fundraising_projects": Project.objects.filter(enable_fundraising=True).order_by("-created_at"),
    }
    return render(request, "project_donations/pledge_list.html", context)


@login_required
def pledge_create(request):
    """Record a new pledge (Feature 6)."""
    if not request.user.has_executive_access():
        messages.error(request, "Executive access required.")
        return redirect("project_donations:pledge_list")

    if request.method == "POST":
        form = PledgeForm(request.POST)
        if form.is_valid():
            pledge = form.save(commit=False)
            pledge.created_by = request.user
            pledge.status = "PENDING"
            pledge.save()
            log_action(
                user=request.user,
                action="CREATE",
                object_type="Pledge",
                object_id=pledge.id,
                ip_address=getattr(request, "client_ip", ""),
                description=f"Recorded pledge: ₦{pledge.pledged_amount:,.2f} by {pledge.member.full_name} for {pledge.project.title}"
            )
            messages.success(request, "Pledge recorded successfully.")
            return redirect("project_donations:pledge_detail", pk=pledge.pk)
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field}: {error}")
    else:
        form = PledgeForm()

    return render(request, "project_donations/pledge_form.html", {
        "form": form,
        "title": "Record Pledge",
        "action": "Save Pledge",
    })


@login_required
def pledge_update(request, pk):
    """Edit a pledge (notes, due date, or cancel it). Executive access required."""
    if not request.user.has_executive_access():
        messages.error(request, "Executive access required.")
        return redirect("project_donations:pledge_list")

    pledge = get_object_or_404(Pledge, pk=pk)

    if request.method == "POST":
        form = PledgeForm(request.POST, instance=pledge)
        if form.is_valid():
            form.save()
            log_action(
                user=request.user,
                action="UPDATE",
                object_type="Pledge",
                object_id=pledge.id,
                ip_address=getattr(request, "client_ip", ""),
                description=f"Updated pledge #{pledge.id}"
            )
            messages.success(request, "Pledge updated successfully.")
            return redirect("project_donations:pledge_detail", pk=pledge.pk)
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field}: {error}")
    else:
        form = PledgeForm(instance=pledge)

    return render(request, "project_donations/pledge_form.html", {
        "form": form,
        "pledge": pledge,
        "title": "Edit Pledge",
        "action": "Update Pledge",
    })


@login_required
def pledge_detail(request, pk):
    """View a pledge with its payment history and a form to record new payments (Feature 7)."""
    pledge = get_object_or_404(
        Pledge.objects.select_related("member", "project", "created_by"), pk=pk
    )
    payments = pledge.payments.select_related("recorded_by").order_by("-payment_date", "-created_at")
    payment_form = PledgePaymentForm(pledge=pledge)

    return render(request, "project_donations/pledge_detail.html", {
        "pledge": pledge,
        "payments": payments,
        "payment_form": payment_form,
        "can_manage": request.user.has_executive_access(),
    })


@login_required
def pledge_delete(request, pk):
    """Delete a pledge (admin only) -- also removes its mirrored payment donations/income via signals."""
    if not request.user.has_admin_access():
        messages.error(request, "Admin access required.")
        return redirect("project_donations:pledge_list")

    pledge = get_object_or_404(Pledge, pk=pk)

    if request.method == "POST":
        member_name = pledge.member.full_name
        amount = pledge.pledged_amount
        pledge.delete()
        log_action(
            user=request.user,
            action="DELETE",
            object_type="Pledge",
            object_id=pk,
            ip_address=getattr(request, "client_ip", ""),
            description=f"Deleted pledge: ₦{amount:,.2f} by {member_name}"
        )
        messages.success(request, "Pledge deleted.")
        return redirect("project_donations:pledge_list")

    return render(request, "project_donations/pledge_confirm_delete.html", {"pledge": pledge})


@login_required
def pledge_payment_create(request, pk):
    """Record a payment (partial or full) against a pledge (Feature 7, 8)."""
    if not request.user.has_executive_access():
        messages.error(request, "Executive access required.")
        return redirect("project_donations:pledge_detail", pk=pk)

    pledge = get_object_or_404(Pledge, pk=pk)

    if pledge.status == "CANCELLED":
        messages.error(request, "Cannot record a payment against a cancelled pledge.")
        return redirect("project_donations:pledge_detail", pk=pk)

    if request.method == "POST":
        form = PledgePaymentForm(request.POST, pledge=pledge)
        if form.is_valid():
            with transaction.atomic():
                payment = form.save(commit=False)
                payment.pledge = pledge
                payment.recorded_by = request.user
                payment.save()
            log_action(
                user=request.user,
                action="CREATE",
                object_type="PledgePayment",
                object_id=payment.id,
                ip_address=getattr(request, "client_ip", ""),
                description=f"Recorded payment ₦{payment.amount:,.2f} on pledge #{pledge.id} ({pledge.member.full_name})"
            )
            messages.success(request, "Payment recorded successfully.")
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field}: {error}")

    return redirect("project_donations:pledge_detail", pk=pk)


@login_required
def pledge_payment_delete(request, pk, payment_pk):
    """Delete a pledge payment (admin only) -- removes the mirrored donation/income via signals."""
    if not request.user.has_admin_access():
        messages.error(request, "Admin access required.")
        return redirect("project_donations:pledge_detail", pk=pk)

    pledge = get_object_or_404(Pledge, pk=pk)
    payment = get_object_or_404(PledgePayment, pk=payment_pk, pledge=pledge)

    if request.method == "POST":
        amount = payment.amount
        payment.delete()
        log_action(
            user=request.user,
            action="DELETE",
            object_type="PledgePayment",
            object_id=payment_pk,
            ip_address=getattr(request, "client_ip", ""),
            description=f"Deleted payment ₦{amount:,.2f} on pledge #{pledge.id}"
        )
        messages.success(request, "Payment deleted.")

    return redirect("project_donations:pledge_detail", pk=pk)


@login_required
@require_http_methods(["POST"])
def pledge_fulfill(request, pk):
    """Mark a Material/Labour (or manually force-closed Money) pledge as
    fulfilled in one step. If this pledge originated from a Project
    Donation, that donation is confirmed automatically too (via the
    sync_pledge_donation signal), including the treasury sync for
    Money/Material donations."""
    if not request.user.has_executive_access():
        messages.error(request, "Executive access required.")
        return redirect("project_donations:pledge_detail", pk=pk)

    pledge = get_object_or_404(Pledge, pk=pk)
    if pledge.status in ("COMPLETED", "CANCELLED"):
        messages.error(request, "This pledge is already closed.")
        return redirect("project_donations:pledge_detail", pk=pk)

    pledge.status = "COMPLETED"
    pledge.save()
    log_action(
        user=request.user,
        action="UPDATE",
        object_type="Pledge",
        object_id=pledge.id,
        ip_address=getattr(request, "client_ip", ""),
        description=f"Marked pledge fulfilled: {pledge.display_value} by {pledge.donor} for {pledge.project.title}"
    )
    messages.success(request, "Pledge marked as fulfilled.")
    return redirect("project_donations:pledge_detail", pk=pk)


@login_required
@require_http_methods(["POST"])
def pledge_cancel(request, pk):
    """Cancel a pledge directly (donor withdrew their commitment). Syncs
    back to the source Donation, if any, via the sync_pledge_donation
    signal."""
    if not request.user.has_executive_access():
        messages.error(request, "Executive access required.")
        return redirect("project_donations:pledge_detail", pk=pk)

    pledge = get_object_or_404(Pledge, pk=pk)
    if pledge.status in ("COMPLETED", "CANCELLED"):
        messages.error(request, "This pledge is already closed.")
        return redirect("project_donations:pledge_detail", pk=pk)

    pledge.status = "CANCELLED"
    pledge.save()
    log_action(
        user=request.user,
        action="UPDATE",
        object_type="Pledge",
        object_id=pledge.id,
        ip_address=getattr(request, "client_ip", ""),
        description=f"Cancelled pledge #{pledge.id} by {pledge.donor} for {pledge.project.title}"
    )
    messages.success(request, "Pledge cancelled.")
    return redirect("project_donations:pledge_detail", pk=pk)
