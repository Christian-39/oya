"""
Models for OYA system settings.
"""
from django.db import models
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.utils import timezone
from decimal import Decimal
from core.models import BaseModel


def logo_upload_path(instance, filename):
    """Upload path for organization logo."""
    ext = filename.split('.')[-1].lower()
    return f"settings/logo.{ext}"


def favicon_upload_path(instance, filename):
    """Upload path for organization favicon."""
    ext = filename.split('.')[-1].lower()
    return f"settings/favicon.{ext}"


class SystemSettings(models.Model):
    """
    Singleton model for system-wide settings.
    Only one row should ever exist in this table.
    """

    THEME_CHOICES = [
        ("LIGHT", "Light"),
        ("DARK", "Dark"),
        ("AUTO", "Auto"),
    ]

    id = models.BigAutoField(primary_key=True)

    # Financial settings
    yearly_dues = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=5000.00,
        verbose_name="Yearly Dues"
    )

    # Membership settings
    minimum_age = models.PositiveIntegerField(
        default=18,
        verbose_name="Minimum Age"
    )
    past_member_age = models.PositiveIntegerField(
        default=56,
        verbose_name="Past Member Age"
    )

    # Appearance settings
    primary_color = models.CharField(
        max_length=7,
        default="#1a237e",
        verbose_name="Primary Color"
    )
    accent_color = models.CharField(
        max_length=7,
        default="#ff6f00",
        verbose_name="Accent Color"
    )
    theme_mode = models.CharField(
        max_length=10,
        choices=THEME_CHOICES,
        default="LIGHT",
        verbose_name="Theme Mode"
    )

    # Association info
    association_name = models.CharField(
        max_length=255,
        default="Okpo Youths Association",
        verbose_name="Association Name"
    )
    motto = models.CharField(
        max_length=100,
        default="PEACE & PROGRESS",
        verbose_name="Motto"
    )

    # Branding
    logo = models.ImageField(
        upload_to=logo_upload_path,
        blank=True,
        null=True,
        verbose_name="Organization Logo",
        help_text="Recommended: PNG with transparent background, max 2MB. Used in header, login page, and emails."
    )
    favicon = models.ImageField(
        upload_to=favicon_upload_path,
        blank=True,
        null=True,
        verbose_name="Browser Favicon",
        help_text="Recommended: 32x32 or 64x64 ICO/PNG, max 1MB. Shown in browser tab."
    )

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "settingsapp_systemsettings"
        verbose_name = "System Settings"
        verbose_name_plural = "System Settings"

    def save(self, *args, **kwargs):
        """Ensure only one instance exists and invalidate cache on change."""
        self.pk = 1
        super().save(*args, **kwargs)
        cache.delete(self.CACHE_KEY)

    def delete(self, *args, **kwargs):
        """Prevent deletion of the singleton instance."""
        pass

    @classmethod
    def load(cls):
        """Load the singleton instance from cache or DB."""
        obj = cache.get(cls.CACHE_KEY)
        if obj is None:
            obj, _ = cls.objects.get_or_create(pk=1)
            cache.set(cls.CACHE_KEY, obj, 3600)  # 1 hour — settings rarely change
        return obj

    def __str__(self):
        return "System Settings"

    @property
    def logo_url(self):
        """Return logo URL or empty string."""
        if self.logo and self.logo.name:
            return self.logo.url
        return ""

    @property
    def favicon_url(self):
        """Return favicon URL or empty string."""
        if self.favicon and self.favicon.name:
            return self.favicon.url
        return ""

    CACHE_KEY = "oya_system_settings_singleton"

class DonationGroup(BaseModel):
    """
    Custom donation-tier group (e.g. G50, Diamond Members, Platinum Donors).
    Names are fully admin-defined — nothing is hardcoded. Only Admin/
    Executive users may create, edit, delete, or activate/deactivate groups
    (enforced in settingsapp.views via AdminRequiredMixin / ExecutiveRequiredMixin).
    """

    id = models.BigAutoField(primary_key=True)
    name = models.CharField(
        max_length=150,
        unique=True,
        verbose_name="Group Name",
        help_text="e.g. G50, Diamond Members, Platinum Donors, Gold Circle"
    )
    description = models.TextField(blank=True, verbose_name="Description")
    minimum_amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
        verbose_name="Minimum Donation Amount"
    )
    maximum_amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal("0.00"))],
        verbose_name="Maximum Donation Amount",
        help_text="Leave blank for unlimited."
    )
    is_active = models.BooleanField(default=True, verbose_name="Active", db_index=True)
    created_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="donation_groups_created",
        verbose_name="Created By"
    )

    class Meta:
        db_table = "settingsapp_donation_group"
        verbose_name = "Donation Group"
        verbose_name_plural = "Donation Groups"
        ordering = ["name"]
        indexes = [
            models.Index(fields=["is_active"]),
            models.Index(fields=["name"]),
        ]

    def __str__(self):
        return self.name

    def clean(self):
        if self.minimum_amount is not None and self.minimum_amount < 0:
            raise ValidationError({"minimum_amount": "Minimum amount cannot be negative."})
        if (
            self.maximum_amount is not None
            and self.minimum_amount is not None
            and self.maximum_amount < self.minimum_amount
        ):
            raise ValidationError({
                "maximum_amount": "Maximum amount cannot be less than the minimum amount."
            })

    @property
    def is_unlimited(self):
        return self.maximum_amount is None

    @property
    def member_count(self):
        return self.memberships.count()

    def confirmed_donations_queryset(self, respect_group_report_exclusion=True):
        """
        Confirmed money donations from members currently in this group.
        When respect_group_report_exclusion is True (the default, used for
        Donation Group reports), projects with include_in_group_reports=False
        are excluded — this affects ONLY group reporting, never treasury,
        finance, or project totals (Feature 4).
        """
        from project_donations.models import Donation
        member_ids = self.memberships.values_list("member_id", flat=True)
        qs = Donation.objects.filter(
            member_id__in=member_ids,
            donor_type="MEMBER",
            donation_type="MONEY",
            status="CONFIRMED",
        ).select_related("project", "member")
        if respect_group_report_exclusion:
            qs = qs.filter(project__include_in_group_reports=True)
        return qs

    @property
    def total_money_donated(self):
        from django.db.models import Sum
        return self.confirmed_donations_queryset().aggregate(
            total=Sum("amount")
        )["total"] or Decimal("0")

    @property
    def total_projects_participated(self):
        return self.confirmed_donations_queryset().values("project").distinct().count()

    @property
    def total_outstanding_pledges(self):
        """Sum of outstanding balances across all non-cancelled pledges from this group's members."""
        from project_donations.models import Pledge
        member_ids = self.memberships.values_list("member_id", flat=True)
        pledges = Pledge.objects.filter(
            member_id__in=member_ids
        ).exclude(status="CANCELLED")
        return sum((p.outstanding_balance for p in pledges), Decimal("0"))


class DonationGroupMembership(models.Model):
    """
    Links a Member to a DonationGroup. A member may belong to multiple
    groups. Tracks when they were added and by whom for auditability.
    """

    id = models.BigAutoField(primary_key=True)
    group = models.ForeignKey(
        DonationGroup,
        on_delete=models.CASCADE,
        related_name="memberships",
        verbose_name="Donation Group"
    )
    member = models.ForeignKey(
        "members.Member",
        on_delete=models.CASCADE,
        related_name="donation_group_memberships",
        verbose_name="Member"
    )
    date_added = models.DateField(default=timezone.now, verbose_name="Date Added")
    added_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="donation_group_assignments_made",
        verbose_name="Added By"
    )

    class Meta:
        db_table = "settingsapp_donation_group_membership"
        verbose_name = "Donation Group Membership"
        verbose_name_plural = "Donation Group Memberships"
        unique_together = ["group", "member"]
        ordering = ["-date_added"]
        indexes = [
            models.Index(fields=["group", "member"]),
            models.Index(fields=["member"]),
        ]

    def __str__(self):
        return f"{self.member} in {self.group}"
