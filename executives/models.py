"""
Models for OYA executives.
"""
from django.db import models
from core.models import BaseModel


class Executive(BaseModel):
    """Executive model for association leadership."""

    POST_CHOICES = [
        ("President", "President"),
        ("Vice President", "Vice President"),
        ("Secretary", "Secretary"),
        ("Assistant Secretary", "Assistant Secretary"),
        ("Treasurer", "Treasurer"),
        ("Financial Secretary", "Financial Secretary"),
        ("Assistant Financial Secretary", "Assistant Financial Secretary"),
        ("PRO", "PRO"),
        ("Assistant PRO", "Assistant PRO"),
        ("DOS", "DOS"),
        ("Assistant DOS", "Assistant DOS"),
        ("Auditor 1", "Auditor 1"),
        ("Auditor 2", "Auditor 2"),
        ("Provost 1", "Provost 1"),
        ("Provost 2", "Provost 2"),
        ("Provost 3", "Provost 3"),
    ]

    id = models.BigAutoField(primary_key=True)
    member = models.ForeignKey(
        "members.Member",
        on_delete=models.PROTECT,
        related_name="executive_roles",
        verbose_name="Member"
    )
    post = models.CharField(
        max_length=50,
        choices=POST_CHOICES,
        verbose_name="Post"
    )
    start_date = models.DateField(verbose_name="Start Date")
    end_date = models.DateField(
        blank=True,
        null=True,
        verbose_name="End Date"
    )
    is_current = models.BooleanField(
        default=True,
        verbose_name="Is Current"
    )
    elected_via = models.ForeignKey(
        "elections.Election",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="executives_elected",
        verbose_name="Elected Via Election",
        help_text=(
            "The election that produced this executive term. Used to group "
            "executives into administrations for Executive Handover Reports. "
            "Left blank for executives who predate this tracking (treated as "
            "the 'Founding Administration')."
        ),
    )

    class Meta:
        db_table = "executives_executive"
        verbose_name = "Executive"
        verbose_name_plural = "Executives"
        ordering = ["-is_current", "-start_date"]
        indexes = [
            models.Index(fields=["is_current"]),
            models.Index(fields=["post"]),
            models.Index(fields=["member"]),
        ]
        unique_together = [["member", "post", "is_current"]]

    def __str__(self):
        return f"{self.post} - {self.member.full_name}"

    def save(self, *args, **kwargs):
        """Override save to manage is_current based on end_date."""
        if self.end_date and self.is_current:
            self.is_current = False
        super().save(*args, **kwargs)
