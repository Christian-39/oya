"""
Views for OYA audit logs.
"""
import logging
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import HttpResponse
from django.template.loader import render_to_string
import csv
from .models import AuditLog

logger = logging.getLogger("oya")


ENTITY_CHOICES = [
    "Member", "Executive", "Finance", "Project","Donation",
    "Case", "Setting", "System", "Election", "Notification"
]


@login_required
def auditlog_list(request):
    """List all audit logs with search and filter."""
    if not request.user.has_executive_access():
        from django.shortcuts import redirect
        from django.contrib import messages
        messages.error(request, "Admin access required.")
        return redirect("dashboard:index")

    queryset = AuditLog.objects.select_related("user").all()

    # Search (global)
    search_term = request.GET.get("search", "").strip()
    if search_term:
        queryset = queryset.filter(
            Q(user__full_name__icontains=search_term) |
            Q(user__serial_number__icontains=search_term) |
            Q(action__icontains=search_term) |
            Q(object_type__icontains=search_term) |
            Q(description__icontains=search_term) |
            Q(ip_address__icontains=search_term)
        )

    # Action filter
    action_filter = request.GET.get("action", "").strip()
    if action_filter:
        queryset = queryset.filter(action=action_filter)

    # Entity (object_type) filter
    entity_filter = request.GET.get("entity", "").strip()
    if entity_filter:
        queryset = queryset.filter(object_type__iexact=entity_filter)

    # User search filter
    user_search = request.GET.get("user_search", "").strip()
    if user_search:
        queryset = queryset.filter(
            Q(user__full_name__icontains=user_search) |
            Q(user__serial_number__icontains=user_search)
        )

    # Date range
    date_from = request.GET.get("date_from", "").strip()
    date_to = request.GET.get("date_to", "").strip()
    if date_from:
        queryset = queryset.filter(created_at__date__gte=date_from)
    if date_to:
        queryset = queryset.filter(created_at__date__lte=date_to)

    # Ordering
    queryset = queryset.order_by("-created_at")

    paginator = Paginator(queryset, 25)
    page = request.GET.get("page", 1)
    logs = paginator.get_page(page)

    context = {
        "logs": logs,
        "paginator": paginator,
        "search_term": search_term,
        "action_filter": action_filter,
        "entity_filter": entity_filter,
        "user_search": user_search,
        "date_from": date_from,
        "date_to": date_to,
        "action_choices": AuditLog.ACTION_CHOICES,
        "entity_choices": ENTITY_CHOICES,
    }
    return render(request, "auditlogs/auditlog_list.html", context)


@login_required
def auditlog_detail(request, pk):
    """Return audit log detail HTML for modal (AJAX)."""
    if not request.user.has_executive_access():
        return HttpResponse("<p class='text-danger'>Access denied.</p>", status=403)

    log = get_object_or_404(AuditLog.objects.select_related("user"), pk=pk)
    html = render_to_string("auditlogs/auditlog_detail.html", {"log": log}, request=request)
    return HttpResponse(html)


@login_required
def auditlog_export(request):
    """Export audit logs to CSV."""
    if not request.user.has_executive_access():
        from django.contrib import messages
        from django.shortcuts import redirect
        messages.error(request, "Admin access required.")
        return redirect("auditlogs:auditlog_list")

    queryset = AuditLog.objects.select_related("user").all().order_by("-created_at")

    # Apply same filters as list view
    search_term = request.GET.get("search", "").strip()
    if search_term:
        queryset = queryset.filter(
            Q(user__full_name__icontains=search_term) |
            Q(action__icontains=search_term) |
            Q(object_type__icontains=search_term) |
            Q(description__icontains=search_term) |
            Q(ip_address__icontains=search_term)
        )
    action_filter = request.GET.get("action", "").strip()
    if action_filter:
        queryset = queryset.filter(action=action_filter)
    entity_filter = request.GET.get("entity", "").strip()
    if entity_filter:
        queryset = queryset.filter(object_type__iexact=entity_filter)
    date_from = request.GET.get("date_from", "").strip()
    date_to = request.GET.get("date_to", "").strip()
    if date_from:
        queryset = queryset.filter(created_at__date__gte=date_from)
    if date_to:
        queryset = queryset.filter(created_at__date__lte=date_to)

    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="audit_logs.csv"'

    writer = csv.writer(response)
    writer.writerow(["ID", "Timestamp", "User", "Action", "Entity", "Object ID", "Description", "IP Address"])

    for log in queryset:
        writer.writerow([
            log.id,
            log.created_at.strftime("%Y-%m-%d %H:%M:%S"),
            log.user.full_name if log.user else "System",
            log.action,
            log.object_type,
            log.object_id or "",
            log.description,
            log.ip_address or "",
        ])

    return response