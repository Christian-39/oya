"""
Signal handlers for OYA.
"""
import logging
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from auditlogs.services import log_action

logger = logging.getLogger("oya")
