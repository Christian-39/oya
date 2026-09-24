"""
Models for OYA operations.
"""
from django.db import models
from core.models import BaseModel


class TaskForceMember(BaseModel):
    """Task force member assignment model."""

    id = models.BigAutoField(primary_key=True)
    member = models.ForeignKey(
        "members.Member",
        on_delete=models.PROTECT,
        related_name="task_force_assignments",
        verbose_name="Member"
    )
    assigned_date = models.DateField(verbose_name="Assigned Date")
    notes = models.TextField(blank=True, verbose_name="Notes")
    is_active = models.BooleanField(default=True, verbose_name="Is Active")

    class Meta:
        db_table = "operations_taskforcemember"
        verbose_name = "Task Force Member"
        verbose_name_plural = "Task Force Members"
        ordering = ["-assigned_date"]
        indexes = [
            models.Index(fields=["is_active"]),
            models.Index(fields=["assigned_date"]),
        ]

    def __str__(self):
        return f"{self.member.full_name} - Task Force"


class Motorcycle(BaseModel):
    """Motorcycle asset tracking model."""

    CONDITION_CHOICES = [
        ("EXCELLENT", "Excellent"),
        ("NEEDS_SERVICE", "Needs Service"),
        ("GROUNDED", "Grounded"),
    ]

    id = models.BigAutoField(primary_key=True)
    asset_tag = models.CharField(
        max_length=50,
        unique=True,
        verbose_name="Asset Tag"
    )
    brand = models.CharField(max_length=100, blank=True, verbose_name="Brand")
    model = models.CharField(max_length=100, blank=True, verbose_name="Model")
    year = models.PositiveIntegerField(blank=True, null=True, verbose_name="Year")
    condition = models.CharField(
        max_length=20,
        choices=CONDITION_CHOICES,
        default="EXCELLENT",
        verbose_name="Condition"
    )
    assigned_to = models.ForeignKey(
        "members.Member",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="assigned_motorcycles",
        verbose_name="Assigned To"
    )

    class Meta:
        db_table = "operations_motorcycle"
        verbose_name = "Motorcycle"
        verbose_name_plural = "Motorcycles"
        ordering = ["asset_tag"]
        indexes = [
            models.Index(fields=["condition"]),
            models.Index(fields=["assigned_to"]),
        ]

    def __str__(self):
        return f"{self.asset_tag} - {self.brand} {self.model}"


class CaseFile(BaseModel):
    """Case file model for tracking disciplinary cases."""

    STATUS_CHOICES = [
        ("OPEN", "Open"),
        ("IN_PROGRESS", "In Progress"),
        ("RESOLVED", "Resolved"),
    ]

    id = models.BigAutoField(primary_key=True)
    case_number = models.CharField(
        max_length=50,
        unique=True,
        blank=True,
        null=True,
        verbose_name="Case Number"
    )
    title = models.CharField(max_length=255, verbose_name="Title")
    description = models.TextField(verbose_name="Description")
    fine_amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=0.00,
        verbose_name="Fine Amount"
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="OPEN",
        verbose_name="Status"
    )
    respondent = models.ForeignKey(
        "members.Member",
        on_delete=models.PROTECT,
        related_name="cases",
        verbose_name="Respondent"
    )
    # NEW: Task-force member who received the report
    reported_to = models.ForeignKey(
        "operations.TaskForceMember",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reported_cases",
        verbose_name="Reported To",
        limit_choices_to={"is_active": True},
    )
    # NEW: Task-force member who resolved the case
    resolved_by = models.ForeignKey(
        "operations.TaskForceMember",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="resolved_cases",
        verbose_name="Resolved By",
        limit_choices_to={"is_active": True},
    )
    created_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        related_name="cases_created",
        verbose_name="Created By"
    )
    resolution_notes = models.TextField(blank=True, verbose_name="Resolution Notes")
    resolved_date = models.DateField(blank=True, null=True, verbose_name="Resolved Date")

    class Meta:
        db_table = "operations_casefile"
        verbose_name = "Case File"
        verbose_name_plural = "Case Files"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["case_number"]),
        ]

    def __str__(self):
        return f"{self.case_number} - {self.title}"

    def save(self, *args, **kwargs):
        # Generate case number on first save only
        if not self.case_number:
            # First commit to obtain a primary key
            super().save(*args, **kwargs)
            self.case_number = f"OYA-CASE-{self.pk:04d}"
            # Update only the case_number to avoid side-effects
            super().save(update_fields=["case_number"])
        else:
            super().save(*args, **kwargs)