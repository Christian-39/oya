"""
Context processors for notifications.
"""
from django.db import models as db_models
from django.core.cache import cache


def unread_notifications(request):
    """Add unread notification count to template context.
    Cached per-user with a 30-second TTL to avoid a COUNT query on
    every single page load."""
    if not request.user.is_authenticated:
        return {"unread_notification_count": 0}

    cache_key = f"unread_notif_count_{request.user.id}"
    count = cache.get(cache_key)
    if count is None:
        from .models import Notification
        count = Notification.objects.filter(
            db_models.Q(recipient=request.user) | db_models.Q(is_global=True),
            is_read=False
        ).count()
        cache.set(cache_key, count, 30)
    return {"unread_notification_count": count}