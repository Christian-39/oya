"""
Models for OYA projects — EXTENDED with fundraising fields.
Replace your existing projects/models.py with this file.
"""
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from decimal import Decimal
from core.models import BaseModel


class Project(BaseModel):
    """Project model for tracking association projects."""

    STATUS_CHOICES = [
        ("FUTURE", "Future"),
        ("AT_HAND", "At Hand"),
        ("FINISHED", "Finished"),
    ]

    FUNDRAISING_STATUS_CHOICES = [
        ("UPCOMING", "Upcoming"),
        ("ACTIVE", "Active"),
        ("CLOSED", "Closed"),
    ]

    id = models.BigAutoField(primary_key=True)
    title = models.CharField(max_length=255, verbose_name="Title")
    budget = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        verbose_name="Budget"
    )
    description = models.TextField(blank=True, verbose_name="Description")
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="FUTURE",
        verbose_name="Status"
    )
    progress_percentage = models.PositiveIntegerField(
        default=0,
        validators=[MaxValueValidator(100)],
        verbose_name="Progress Percentage"
    )

    # ─── FUNDRAISING FIELDS ───
    enable_fundraising = models.BooleanField(
        default=False,
        verbose_name="Enable Fundraising",
        help_text="Allow donations to be raised for this project."
    )
    target_amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
        verbose_name="Target Amount"
    )
    fundraising_amount_raised = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal("0.00"),
        verbose_name="Amount Raised",
        help_text="Automatically updated from confirmed donations."
    )
    fundraising_remaining_amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal("0.00"),
        verbose_name="Remaining Amount",
        help_text="Automatically calculated from target minus raised."
    )
    fundraising_progress_percentage = models.PositiveIntegerField(
        default=0,
        validators=[MaxValueValidator(100)],
        verbose_name="Progress Percentage",
        help_text="Automatically calculated fundraising progress."
    )
    fundraising_start_date = models.DateField(
        null=True,
        blank=True,
        verbose_name="Fundraising Start Date"
    )
    fundraising_end_date = models.DateField(
        null=True,
        blank=True,
        verbose_name="Fundraising End Date"
    )
    fundraising_status = models.CharField(
        max_length=20,
        choices=FUNDRAISING_STATUS_CHOICES,
        default="UPCOMING",
        verbose_name="Fundraising Status"
    )

    # ─── DONATION GROUP REPORTING ───
    include_in_group_reports = models.BooleanField(
        default=True,
        verbose_name="Include in Donation Group Reports?",
        help_text=(
            "If disabled, this project's donations are excluded from donation "
            "group reports only. Treasury, finance, and project totals are "
            "unaffected and donation records remain intact."
        )
    )

    class Meta:
        db_table = "projects_project"
        verbose_name = "Project"
        verbose_name_plural = "Projects"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["progress_percentage"]),
            models.Index(fields=["enable_fundraising"]),
            models.Index(fields=["fundraising_status"]),
            models.Index(fields=["include_in_group_reports"]),
        ]

    def __str__(self):
        return self.title

    def is_future(self):
        return self.status == "FUTURE"

    def is_at_hand(self):
        return self.status == "AT_HAND"

    def is_finished(self):
        return self.status == "FINISHED"

    def update_fundraising_stats(self):
        """Update fundraising statistics from confirmed donations."""
        from django.db.models import Sum
        from project_donations.models import Donation

        total_raised = Donation.objects.filter(
            project=self, status="CONFIRMED"
        ).aggregate(total=Sum("amount"))["total"] or Decimal("0")

        self.fundraising_amount_raised = total_raised
        if self.target_amount and self.target_amount > 0:
            self.fundraising_remaining_amount = max(
                self.target_amount - total_raised, Decimal("0")
            )
            self.fundraising_progress_percentage = min(
                int((total_raised / self.target_amount) * 100), 100
            )
        else:
            self.fundraising_remaining_amount = Decimal("0")
            self.fundraising_progress_percentage = 0

        # Auto-update fundraising status based on dates
        today = timezone.now().date()
        if self.fundraising_start_date and self.fundraising_end_date:
            if today < self.fundraising_start_date:
                self.fundraising_status = "UPCOMING"
            elif today > self.fundraising_end_date:
                self.fundraising_status = "CLOSED"
            else:
                self.fundraising_status = "ACTIVE"
        elif self.fundraising_start_date and not self.fundraising_end_date:
            self.fundraising_status = "ACTIVE" if today >= self.fundraising_start_date else "UPCOMING"

        self.save(update_fields=[
            "fundraising_amount_raised",
            "fundraising_remaining_amount",
            "fundraising_progress_percentage",
            "fundraising_status"
        ])

    @property
    def total_member_donations(self):
        from django.db.models import Sum
        from project_donations.models import Donation
        return Donation.objects.filter(
            project=self, donor_type="MEMBER", status="CONFIRMED"
        ).aggregate(total=Sum("amount"))["total"] or Decimal("0")

    @property
    def total_outside_donations(self):
        from django.db.models import Sum
        from project_donations.models import Donation
        return Donation.objects.filter(
            project=self, donor_type="OUTSIDE", status="CONFIRMED"
        ).aggregate(total=Sum("amount"))["total"] or Decimal("0")

    @property
    def total_donors_count(self):
        from project_donations.models import Donation
        return Donation.objects.filter(
            project=self, status="CONFIRMED"
        ).values("member", "outside_donor").distinct().count()