"""
Views for OYA notifications.
"""
import logging
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import JsonResponse
from auditlogs.services import log_action
from .models import Notification
from .forms import NotificationForm

logger = logging.getLogger("oya")


@login_required
def notification_list(request):
    """List notifications for the current user."""
    if request.user.has_admin_access():
        queryset = Notification.objects.all()
    else:
        queryset = Notification.objects.filter(
            Q(recipient=request.user) | Q(is_global=True)
        )

    # Search
    search_term = request.GET.get("search", "")
    if search_term:
        queryset = queryset.filter(
            Q(title__icontains=search_term) |
            Q(message__icontains=search_term)
        )

    # Type filter
    type_filter = request.GET.get("type", "")
    if type_filter:
        queryset = queryset.filter(notification_type=type_filter)

    # Read filter
    read_filter = request.GET.get("read", "")
    if read_filter == "unread":
        queryset = queryset.filter(is_read=False)
    elif read_filter == "read":
        queryset = queryset.filter(is_read=True)

    # Ordering
    queryset = queryset.order_by("-created_at")

    paginator = Paginator(queryset, 25)
    page = request.GET.get("page", 1)
    notifications = paginator.get_page(page)

    # Counts for tabs
    if request.user.has_admin_access():
        base_queryset = Notification.objects.all()
    else:
        base_queryset = Notification.objects.filter(
            Q(recipient=request.user) | Q(is_global=True)
        )

    total_count = base_queryset.count()
    unread_count = base_queryset.filter(is_read=False).count()
    alert_count = base_queryset.filter(notification_type="ERROR").count()
    system_count = base_queryset.filter(notification_type="SYSTEM").count()

    context = {
        "notifications": notifications,
        "search_term": search_term,
        "type_filter": type_filter,
        "read_filter": read_filter,
        "type_choices": Notification.NOTIFICATION_TYPES,
        "total_count": total_count,
        "unread_count": unread_count,
        "alert_count": alert_count,
        "system_count": system_count,
    }
    return render(request, "notifications/notification_list.html", context)


@login_required
def notification_detail(request, pk):
    """Display and mark notification as read."""
    notification = get_object_or_404(Notification, pk=pk)

    # Check permission
    if not notification.is_global and notification.recipient != request.user:
        if not request.user.has_admin_access():
            messages.error(request, "You do not have permission to view this notification.")
            return redirect("notifications:notification_list")

    notification.mark_as_read()
    return render(request, "notifications/notification_detail.html", {"notification": notification})


@login_required
def notification_create(request):
    """Create a new notification (admin and executive)."""
    if not request.user.has_executive_access():
        messages.error(request, "Executive access required.")
        return redirect("notifications:notification_list")

    if request.method == "POST":
        form = NotificationForm(request.POST)
        if form.is_valid():
            notification = form.save()
            log_action(
                user=request.user,
                action="CREATE",
                object_type="Notification",
                object_id=notification.id,
                ip_address=getattr(request, "client_ip", ""),
                description=f"Created notification: {notification.title}"
            )
            messages.success(request, "Notification sent successfully.")
            return redirect("notifications:notification_list")
        else:
            for error in form.errors.values():
                messages.error(request, error)
    else:
        form = NotificationForm()

    return render(request, "notifications/notification_form.html", {
        "form": form,
        "title": "Send Notification",
        "action": "Send"
    })


@login_required
def mark_all_read(request):
    """Mark all notifications as read for current user."""
    if request.method == "POST":
        if request.user.has_admin_access():
            Notification.objects.filter(is_read=False).update(is_read=True)
        else:
            Notification.objects.filter(
                Q(recipient=request.user) | Q(is_global=True),
                is_read=False
            ).update(is_read=True)
        messages.success(request, "All notifications marked as read.")
    return redirect("notifications:notification_list")


@login_required
def notification_delete(request, pk):
    """Delete a notification."""
    if not request.user.has_admin_access():
        messages.error(request, "Admin access required.")
        return redirect("notifications:notification_list")

    notification = get_object_or_404(Notification, pk=pk)

    if request.method == "POST":
        notification.delete()
        log_action(
            user=request.user,
            action="DELETE",
            object_type="Notification",
            object_id=pk,
            ip_address=getattr(request, "client_ip", ""),
            description=f"Deleted notification: {notification.title}"
        )
        messages.success(request, "Notification deleted.")
        return redirect("notifications:notification_list")

    return render(request, "notifications/notification_confirm_delete.html", {"notification": notification})