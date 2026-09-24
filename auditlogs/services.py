"""
Services for OYA audit logging.
"""
import logging
from .models import AuditLog

logger = logging.getLogger("oya")


def log_action(user, action, object_type, object_id=None,
               description="", ip_address=""):
    """
    Create an audit log entry.

    Args:
        user: The user performing the action
        action: The action type (CREATE, UPDATE, DELETE, etc.)
        object_type: The type of object being acted upon
        object_id: The ID of the object (optional)
        description: Detailed description of the action
        ip_address: IP address of the user

    Returns:
        AuditLog: The created audit log entry
    """
    try:
        audit_log = AuditLog.objects.create(
            user=user if user and user.is_authenticated else None,
            action=action,
            object_type=object_type,
            object_id=object_id,
            description=description,
            ip_address=ip_address if ip_address else ""
        )
        return audit_log
    except Exception as e:
        logger.error(f"Failed to create audit log: {e}")
        return None


def get_client_ip(request):
    """Extract client IP from request."""
    x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if x_forwarded_for:
        ip = x_forwarded_for.split(",")[0].strip()
    else:
        ip = request.META.get("REMOTE_ADDR", "")
    return ip


def log_request_action(request, action, object_type, object_id=None, description=""):
    """
    Convenience helper that auto-extracts user and IP from request.

    Usage in views:
        from auditlogs.services import log_request_action
        log_request_action(request, "CREATE", "Member", member.id, f"Created member {member.full_name}")
    """
    return log_action(
        user=request.user,
        action=action,
        object_type=object_type,
        object_id=object_id,
        description=description,
        ip_address=get_client_ip(request)
    )


def get_recent_logs(limit=50):
    """Get recent audit logs."""
    return AuditLog.objects.select_related("user").order_by("-created_at")[:limit]


def get_logs_by_user(user, limit=50):
    """Get audit logs for a specific user."""
    return AuditLog.objects.filter(user=user).select_related("user").order_by("-created_at")[:limit]


def get_logs_by_action(action, limit=50):
    """Get audit logs for a specific action type."""
    return AuditLog.objects.filter(action=action).select_related("user").order_by("-created_at")[:limit]


def get_logs_by_entity(object_type, limit=50):
    """Get audit logs for a specific entity type."""
    return AuditLog.objects.filter(object_type__iexact=object_type).select_related("user").order_by("-created_at")[:limit]