"""
Models for OYA notifications.
"""
from django.db import models
from core.models import BaseModel


class Notification(BaseModel):
    """Notification model for system alerts and messages."""

    NOTIFICATION_TYPES = [
        ("INFO", "Info"),
        ("SUCCESS", "Success"),
        ("WARNING", "Warning"),
        ("ERROR", "Error"),
        ("ELECTION", "Election"),
        ("FINANCE", "Finance"),
        ("PROJECT", "Project"),
        ("CASE", "Case"),
        ("SYSTEM", "System"),
    ]

    id = models.BigAutoField(primary_key=True)
    title = models.CharField(max_length=255, verbose_name="Title")
    message = models.TextField(verbose_name="Message")
    notification_type = models.CharField(
        max_length=20,
        choices=NOTIFICATION_TYPES,
        default="INFO",
        verbose_name="Type"
    )
    recipient = models.ForeignKey(
        "accounts.User",
        on_delete=models.CASCADE,
        related_name="notifications",
        verbose_name="Recipient",
        blank=True,
        null=True
    )
    is_read = models.BooleanField(default=False, verbose_name="Is Read")
    is_global = models.BooleanField(
        default=False,
        verbose_name="Is Global"
    )

    class Meta:
        db_table = "notifications_notification"
        verbose_name = "Notification"
        verbose_name_plural = "Notifications"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["recipient", "is_read"]),
            models.Index(fields=["notification_type"]),
            models.Index(fields=["is_global"]),
            models.Index(fields=["created_at"]),
        ]

    def __str__(self):
        return self.title

    def mark_as_read(self):
        """Mark notification as read."""
        if not self.is_read:
            self.is_read = True
            self.save(update_fields=["is_read"])
