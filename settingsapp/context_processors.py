"""
Context processors for system settings.
"""
from .models import SystemSettings


def system_settings(request):
    """Add system settings to template context."""
    try:
        settings_obj = SystemSettings.load()
        return {
            "system_settings": settings_obj,
            "association_name": settings_obj.association_name,
            "motto": settings_obj.motto,
            "primary_color": settings_obj.primary_color,
            "accent_color": settings_obj.accent_color,
            "theme_mode": settings_obj.theme_mode,
            "settings_logo_url": settings_obj.logo_url,
            "settings_favicon_url": settings_obj.favicon_url,
        }
    except Exception:
        return {
            "system_settings": None,
            "association_name": "Okpo Youths Association",
            "motto": "PEACE & PROGRESS",
            "primary_color": "#1a237e",
            "accent_color": "#ff6f00",
            "theme_mode": "LIGHT",
            "settings_logo_url": "",
            "settings_favicon_url": "",
        }
