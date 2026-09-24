"""
Context processors for OYA core.
"""
from django.conf import settings
from members.models import Member

def user_member(request):
    """Add user's member record to all template contexts.
    Delegates to the cached User.member property so there is exactly
    one code path and one query per request."""
    if request.user.is_authenticated:
        return {"user_member": request.user.member}
    return {"user_member": None}


def oya_settings(request):
    """Add OYA settings to template context."""
    return {
        "OYA_SETTINGS": settings.OYA_SETTINGS,
        "CURRENCY_SYMBOL": settings.OYA_SETTINGS["CURRENCY_SYMBOL"],
    }