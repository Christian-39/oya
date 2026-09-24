"""
Models for OYA members.
"""
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.core.exceptions import ValidationError
from django.conf import settings
from django.utils import timezone
from django.utils.functional import cached_property
from core.models import BaseModel


NIGERIAN_STATES = [
    ("Abia", "Abia"),
    ("Adamawa", "Adamawa"),
    ("Akwa Ibom", "Akwa Ibom"),
    ("Anambra", "Anambra"),
    ("Bauchi", "Bauchi"),
    ("Bayelsa", "Bayelsa"),
    ("Benue", "Benue"),
    ("Borno", "Borno"),
    ("Cross River", "Cross River"),
    ("Delta", "Delta"),
    ("Ebonyi", "Ebonyi"),
    ("Edo", "Edo"),
    ("Ekiti", "Ekiti"),
    ("Enugu", "Enugu"),
    ("FCT", "Federal Capital Territory"),
    ("Gombe", "Gombe"),
    ("Imo", "Imo"),
    ("Jigawa", "Jigawa"),
    ("Kaduna", "Kaduna"),
    ("Kano", "Kano"),
    ("Katsina", "Katsina"),
    ("Kebbi", "Kebbi"),
    ("Kogi", "Kogi"),
    ("Kwara", "Kwara"),
    ("Lagos", "Lagos"),
    ("Nasarawa", "Nasarawa"),
    ("Niger", "Niger"),
    ("Ogun", "Ogun"),
    ("Ondo", "Ondo"),
    ("Osun", "Osun"),
    ("Oyo", "Oyo"),
    ("Plateau", "Plateau"),
    ("Rivers", "Rivers"),
    ("Sokoto", "Sokoto"),
    ("Taraba", "Taraba"),
    ("Yobe", "Yobe"),
    ("Zamfara", "Zamfara"),
]


class Clan(models.Model):
    """Clan/Umu Nna model."""
    id = models.BigAutoField(primary_key=True)
    name = models.CharField(max_length=100, unique=True, verbose_name="Clan Name")

    class Meta:
        db_table = "members_clan"
        verbose_name = "Clan"
        verbose_name_plural = "Clans"
        ordering = ["name"]

    def __str__(self):
        return self.name


class Member(BaseModel):
    """Member model for Okpo Youths Association."""

    STATUS_CHOICES = [
        ("ACTIVE", "Active"),
        ("PAST_MEMBER", "Past Member"),
        ("REMOVED", "Removed"),
    ]

    id = models.BigAutoField(primary_key=True)
    serial_number = models.CharField(
        max_length=20,
        unique=True,
        verbose_name="Serial Number"
    )
    full_name = models.CharField(max_length=255, verbose_name="Full Name")
    phone = models.CharField(max_length=20, blank=True, verbose_name="Phone")
    age = models.PositiveIntegerField(
        validators=[
            MinValueValidator(18, message="Age must be at least 18."),
            MaxValueValidator(55, message="Age must not exceed 55.")
        ],
        verbose_name="Age"
    )
    umu_nna_clan = models.ForeignKey(
        Clan,
        on_delete=models.PROTECT,
        related_name="members",
        verbose_name="Umu Nna Clan"
    )
    photo = models.ImageField(
        upload_to="members/photos/%Y/%m/",
        blank=True,
        null=True,
        verbose_name="Photo"
    )
    # Location: dropdown for Nigerian states, or free text for abroad
    state_or_abroad = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="State or Abroad"
    )
    is_abroad = models.BooleanField(
        default=False,
        verbose_name="Living Abroad?"
    )
    # Year the member joined the association - affects dues calculation
    year_joined = models.PositiveIntegerField(
        verbose_name="Year Joined",
        help_text="The year this member joined the association. Dues will only be tracked from this year onward.",
        default=2020,
        validators=[MinValueValidator(2020, message="Join year cannot be before platform creation (2020).")]
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="ACTIVE",
        verbose_name="Status"
    )
    offense_committed = models.TextField(
        blank=True,
        verbose_name="Offense Committed"
    )
    removal_reason = models.TextField(
        blank=True,
        verbose_name="Removal Reason"
    )

    class Meta:
        db_table = "members_member"
        verbose_name = "Member"
        verbose_name_plural = "Members"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["umu_nna_clan"]),
            models.Index(fields=["serial_number"]),
            models.Index(fields=["full_name"]),
            models.Index(fields=["year_joined"]),
        ]

    def __str__(self):
        return f"{self.serial_number} - {self.full_name}"

    @cached_property
    def position(self):
        """Return the current executive post if the member is an executive.
        Uses the prefetched cache when available (zero extra queries),
        otherwise one query cached for the life of the instance."""
        for role in self.executive_roles.all():
            if role.is_current:
                return role.post
        return None

    @property
    def is_taskforce(self):
        """Check if the member is currently assigned to the task force."""
        return self.task_force_assignments.filter(is_active=True).exists()

    def clean(self):
        """Model-level validation for age and year_joined."""
        if self.age and (self.age < 18 or self.age > 55):
            raise ValidationError({
                "age": "Age must be between 18 and 55 years."
            })
        current_year = timezone.now().year
        if self.year_joined and self.year_joined > current_year:
            raise ValidationError({
                "year_joined": "Join year cannot be in the future."
            })
        super().clean()

    def is_active_member(self):
        """Check if member is currently active."""
        return self.status == "ACTIVE"

    def is_past_member(self):
        """Check if member is a past member."""
        return self.status == "PAST_MEMBER"

    def is_removed(self):
        """Check if member has been removed."""
        return self.status == "REMOVED"

    def age_check(self):
        """Check if member is within valid age range."""
        return 18 <= self.age <= 55

    def should_be_past_member(self):
        """Check if member should be moved to past member status."""
        return self.age >= 56 and self.status == "ACTIVE"