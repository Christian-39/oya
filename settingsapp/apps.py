"""
App configuration for settingsapp.
"""
from django.apps import AppConfig


class SettingsappConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "settingsapp"
    verbose_name = "Settings"
