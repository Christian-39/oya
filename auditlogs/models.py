"""
Models for OYA audit logs.
"""
from django.db import models


class AuditLog(models.Model):
    """Audit log model for tracking all system actions."""

    ACTION_CHOICES = [
        ("CREATE", "Create"),
        ("UPDATE", "Update"),
        ("DELETE", "Delete"),
        ("LOGIN", "Login"),
        ("LOGOUT", "Logout"),
        ("PIN_RESET", "PIN Reset"),
        ("ELECTION_ACTION", "Election Action"),
        ("FINANCE_ACTION", "Finance Action"),
        ("PROJECT_ACTION", "Project Action"),
        ("CASE_ACTION", "Case Action"),
        ("PERMISSION_CHANGE", "Permission Change"),
        ("VIEW", "View"),
    ]

    id = models.BigAutoField(primary_key=True)
    user = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="audit_logs",
        verbose_name="User"
    )
    action = models.CharField(
        max_length=30,
        choices=ACTION_CHOICES,
        verbose_name="Action"
    )
    object_type = models.CharField(
        max_length=100,
        verbose_name="Object Type"
    )
    object_id = models.BigIntegerField(
        blank=True,
        null=True,
        verbose_name="Object ID"
    )
    description = models.TextField(
        blank=True,
        verbose_name="Description"
    )
    ip_address = models.GenericIPAddressField(
        blank=True,
        null=True,
        verbose_name="IP Address"
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Created At")

    class Meta:
        db_table = "auditlogs_auditlog"
        verbose_name = "Audit Log"
        verbose_name_plural = "Audit Logs"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user"]),
            models.Index(fields=["action"]),
            models.Index(fields=["object_type"]),
            models.Index(fields=["created_at"]),
            models.Index(fields=["ip_address"]),
        ]

    def __str__(self):
        return f"{self.action} - {self.object_type} by {self.user}"
