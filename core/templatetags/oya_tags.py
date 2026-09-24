"""
Custom template tags for OYA.
"""
from django import template
from django.contrib.humanize.templatetags.humanize import intcomma

register = template.Library()


@register.filter
def naira(value):
    """Format a number as Nigerian Naira."""
    try:
        value = float(value)
        return f"\u20a6{value:,.2f}"
    except (ValueError, TypeError):
        return f"\u20a60.00"


@register.filter
def naira_int(value):
    """Format a number as Nigerian Naira without decimal places."""
    try:
        value = float(value)
        return f"\u20a6{value:,.0f}"
    except (ValueError, TypeError):
        return "\u20a60"


@register.filter
def status_badge(value):
    """Return a Bootstrap badge class for a status."""
    status_classes = {
        "ACTIVE": "success",
        "PAST_MEMBER": "info",
        "REMOVED": "danger",
        "OPEN": "warning",
        "IN_PROGRESS": "primary",
        "RESOLVED": "success",
        "FUTURE": "secondary",
        "AT_HAND": "primary",
        "FINISHED": "success",
        "EXCELLENT": "success",
        "NEEDS_SERVICE": "warning",
        "GROUNDED": "danger",
        "UPCOMING": "info",
        "ONGOING": "primary",
        "COMPLETED": "success",
        "CANCELLED": "danger",
        "ADMIN": "danger",
        "EXECUTIVE": "primary",
        "FLOOR_MEMBER": "success",
    }
    return status_classes.get(value.upper() if value else "", "secondary")


@register.simple_tag(takes_context=True)
def query_transform(context, **kwargs):
    query = context["request"].GET.copy()
    for k, v in kwargs.items():
        query[k] = v
    for k in list(query.keys()):
        if query[k] == "" or query[k] is None:
            del query[k]
    return query.urlencode()