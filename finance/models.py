"""Models for OYA finance."""
from django.db import models, transaction
from django.core.validators import MinValueValidator
from django.core.exceptions import ValidationError
from django.utils import timezone
from decimal import Decimal
from core.models import BaseModel


class Income(BaseModel):
    """Income model for tracking association revenue."""

    INCOME_TYPE_CHOICES = [
        ("DUES", "Yearly Dues"),
        ("DONATION", "Donation / Contribution"),
        ("EVENT", "Event Fee"),
        ("CASE_FINE", "Case Fine / Resolution"),
        ("OTHER", "Other"),
    ]

    id = models.BigAutoField(primary_key=True)
    income_type = models.CharField(
        max_length=20,
        choices=INCOME_TYPE_CHOICES,
        default="DONATION",
        verbose_name="Income Type",
        db_index=True,
    )
    amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
        verbose_name="Amount"
    )
    reason = models.CharField(max_length=255, verbose_name="Reason")

    # Link to member for searchable contributions
    member = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="contributions",
        verbose_name="Member",
        limit_choices_to={"is_active": True},
        help_text="Select if the contributor is a registered member"
    )

    # NEW: Link to the case file that generated this fine
    case = models.ForeignKey(
        "operations.CaseFile",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="income_records",
        verbose_name="Related Case",
        help_text="Select the resolved case this fine was collected from"
    )

    paid_by = models.CharField(
        max_length=255,
        blank=True,
        verbose_name="Paid By",
        help_text="Name of payer (used if no member is selected)"
    )
    created_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        related_name="incomes_created",
        verbose_name="Created By"
    )

    class Meta:
        db_table = "finance_income"
        verbose_name = "Income"
        verbose_name_plural = "Income"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["created_at"]),
            models.Index(fields=["income_type"]),
            models.Index(fields=["member"]),
            models.Index(fields=["case"]),
        ]

    def __str__(self):
        return f"NGN {self.amount:,.2f} - {self.reason}"

    def get_payer_display(self):
        """Return member name if linked, else paid_by text."""
        if self.member:
            return self.member.get_full_name()
        return self.paid_by or "Anonymous"


class DuesPaymentTransaction(BaseModel):
    """
    Represents a single dues payment event from an administrator.
    A single transaction may be allocated across multiple years.
    """
    PAYMENT_METHOD_CHOICES = [
        ("CASH", "Cash"),
        ("BANK_TRANSFER", "Bank Transfer"),
        ("MOBILE_MONEY", "Mobile Money"),
        ("CHECK", "Check"),
        ("OTHER", "Other"),
    ]

    id = models.BigAutoField(primary_key=True)
    member = models.ForeignKey(
        "accounts.User",
        on_delete=models.CASCADE,
        related_name="dues_transactions",
        verbose_name="Member",
        limit_choices_to={"is_active": True},
    )
    total_amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
        verbose_name="Total Amount Paid",
    )
    payment_method = models.CharField(
        max_length=20,
        choices=PAYMENT_METHOD_CHOICES,
        default="CASH",
        verbose_name="Payment Method",
    )
    receipt_reference = models.CharField(
        max_length=255,
        blank=True,
        verbose_name="Receipt / Reference Number",
        help_text="Bank transfer reference, receipt number, or any proof of payment ID.",
    )
    payment_date = models.DateField(
        verbose_name="Payment Date",
        default=timezone.now,
    )
    notes = models.TextField(
        blank=True,
        verbose_name="Notes",
    )
    recorded_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        related_name="dues_transactions_recorded",
        verbose_name="Recorded By",
    )

    class Meta:
        db_table = "finance_association_dues"
        verbose_name = "Dues Payment Transaction"
        verbose_name_plural = "Dues Payment Transactions"
        ordering = ["-payment_date", "-created_at"]

    def __str__(self):
        return f"{self.member.get_full_name()} — ₦{self.total_amount:,.2f} on {self.payment_date}"


class DuesPayment(BaseModel):
    """
    Tracks the payment status for a single member for a single year.
    Platform started 2020. Dues = ₦5,000/year (fixed).
    amount_paid accumulates across multiple payment transactions.
    """
    YEARLY_DUES_AMOUNT = Decimal("5000")

    STATUS_PAID = "PAID"
    STATUS_PARTIAL = "PARTIAL"
    STATUS_OWED = "OWED"
    STATUS_PREPAID = "PREPAID"
    STATUS_NOT_APPLICABLE = "N/A"  # Years before member joined
    STATUS_CHOICES = [
        (STATUS_PAID, "Paid"),
        (STATUS_PARTIAL, "Partially Paid"),
        (STATUS_OWED, "Owed"),
        (STATUS_PREPAID, "Prepaid"),
        (STATUS_NOT_APPLICABLE, "Not Applicable"),
    ]

    id = models.BigAutoField(primary_key=True)
    member = models.ForeignKey(
        "accounts.User",
        on_delete=models.CASCADE,
        related_name="dues_payments",
        verbose_name="Member",
        limit_choices_to={"is_active": True},
    )
    year = models.PositiveIntegerField(
        verbose_name="Dues Year",
        help_text="The calendar year this dues payment covers.",
        db_index=True,
    )
    amount_paid = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal("0"),
        verbose_name="Amount Paid",
        help_text="Cumulative amount paid for this year. May be partial.",
    )
    income = models.OneToOneField(
        Income,
        on_delete=models.CASCADE,
        related_name="dues_payment",
        verbose_name="Linked Income Record",
        null=True,
        blank=True,
    )
    notes = models.TextField(
        blank=True,
        verbose_name="Notes",
        help_text="e.g., 'Paid in cash at meeting', 'Bank transfer ref: XYZ'",
    )
    recorded_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        related_name="dues_recorded",
        verbose_name="Recorded By",
    )
    # Track which transaction(s) contributed to this record
    transactions = models.ManyToManyField(
        DuesPaymentTransaction,
        related_name="dues_allocations",
        blank=True,
        verbose_name="Source Transactions",
    )

    class Meta:
        db_table = "finance_dues_payment"
        verbose_name = "Dues Payment"
        verbose_name_plural = "Dues Payments"
        ordering = ["-year", "member__full_name"]
        unique_together = ["member", "year"]
        constraints = [
            models.CheckConstraint(
                check=models.Q(year__gte=2020),
                name="year_gte_2020",
            ),
            models.CheckConstraint(
                check=models.Q(amount_paid__gte=0),
                name="amount_paid_gte_zero",
            ),
        ]

    def __str__(self):
        status_label = dict(self.STATUS_CHOICES).get(self.status, self.status)
        return f"{self.member.get_full_name()} — {self.year} Dues ({status_label})"

    def clean(self):
        if self.year < 2020:
            raise ValidationError({"year": "Dues year cannot be before platform creation (2020)."})
        if self.amount_paid < 0:
            raise ValidationError({"amount_paid": "Amount paid cannot be negative."})

    @property
    def status(self):
        current_year = timezone.now().year
        # Check if this year is before the member's join year
        join_year = self.get_member_join_year(self.member)
        if self.year < join_year:
            return self.STATUS_NOT_APPLICABLE
        if self.amount_paid >= self.YEARLY_DUES_AMOUNT:
            if self.year > current_year:
                return self.STATUS_PREPAID
            return self.STATUS_PAID
        elif self.amount_paid > 0:
            return self.STATUS_PARTIAL
        return self.STATUS_OWED

    def get_status_display(self):
        return dict(self.STATUS_CHOICES).get(self.status, self.status)


    @property
    def remaining_balance(self):
        """Amount still needed to fully pay this year's dues."""
        # If year is before join year, no balance needed
        join_year = self.get_member_join_year(self.member)
        if self.year < join_year:
            return Decimal("0")
        return max(self.YEARLY_DUES_AMOUNT - self.amount_paid, Decimal("0"))

    @property
    def is_fully_paid(self):
        return self.amount_paid >= self.YEARLY_DUES_AMOUNT

    @classmethod
    def get_member_join_year(cls, member):
        """Determine the first year a member should owe dues."""
        platform_start = 2020
        # First priority: year_joined field on member/User
        join_year = getattr(member, "year_joined", None)
        if join_year and isinstance(join_year, int) and join_year >= platform_start:
            return join_year
        # Fallback: try to extract from serial number (e.g., OYA-2024-0001)
        serial = getattr(member, "serial_number", "")
        if serial:
            parts = serial.split("-")
            if len(parts) >= 2:
                try:
                    year_from_serial = int(parts[1])
                    if year_from_serial >= platform_start:
                        return year_from_serial
                except (ValueError, IndexError):
                    pass
        # Final fallback: the member's actual registration date. Never
        # blindly default to the platform's inception year — that would
        # retroactively charge dues to years before the member existed at
        # all if year_joined is ever missing/invalid and the serial number
        # doesn't parse to a year.
        registration_date = getattr(member, "created_at", None) or getattr(member, "date_joined", None)
        if registration_date:
            registration_year = registration_date.year
            if registration_year >= platform_start:
                return registration_year
        return platform_start

    @classmethod
    def get_outstanding_years(cls, member):
        """
        Return a list of years the member owes dues for, sorted oldest first.
        Each item is a dict with year, amount_paid, remaining_balance, status.
        Only includes years from join_year onward.
        """
        current_year = timezone.now().year
        join_year = cls.get_member_join_year(member)
        start_year = max(join_year, 2020)

        # Get all existing payment records for this member
        existing = {
            dp.year: dp
            for dp in cls.objects.filter(member=member)
        }

        outstanding = []
        for year in range(start_year, current_year + 1):
            dp = existing.get(year)
            if dp:
                if not dp.is_fully_paid:
                    outstanding.append({
                        "year": year,
                        "amount_paid": dp.amount_paid,
                        "remaining_balance": dp.remaining_balance,
                        "status": dp.status,
                        "record": dp,
                    })
            else:
                outstanding.append({
                    "year": year,
                    "amount_paid": Decimal("0"),
                    "remaining_balance": cls.YEARLY_DUES_AMOUNT,
                    "status": cls.STATUS_OWED,
                    "record": None,
                })
        return outstanding

    @classmethod
    def get_member_debt(cls, member):
        """
        Calculate total dues debt for a member.
        Debt = sum of remaining balances for all years from join_year to current_year.
        Years before join_year are not counted.
        """
        current_year = timezone.now().year
        join_year = cls.get_member_join_year(member)
        start_year = max(join_year, 2020)

        expected_years = list(range(start_year, current_year + 1))
        total_expected = len(expected_years) * cls.YEARLY_DUES_AMOUNT

        total_paid = cls.objects.filter(
            member=member,
            year__in=expected_years,
        ).aggregate(total=models.Sum("amount_paid"))["total"] or Decimal("0")

        # Also include prepaid amounts as "paid" (they reduce debt)
        prepaid_paid = cls.objects.filter(
            member=member,
            year__gt=current_year,
        ).aggregate(total=models.Sum("amount_paid"))["total"] or Decimal("0")

        years_paid_qs = cls.objects.filter(
            member=member,
            year__in=expected_years,
            amount_paid__gte=cls.YEARLY_DUES_AMOUNT,
        ).values_list("year", flat=True)

        return {
            "total_expected": total_expected,
            "total_paid": total_paid,
            "prepaid_amount": prepaid_paid,
            "debt_owed": max(total_expected - total_paid, Decimal("0")),
            "years_expected": expected_years,
            "years_paid": list(years_paid_qs),
            "years_partial": list(
                cls.objects.filter(
                    member=member,
                    year__in=expected_years,
                    amount_paid__gt=0,
                    amount_paid__lt=cls.YEARLY_DUES_AMOUNT,
                ).values_list("year", flat=True)
            ),
            "join_year": join_year,
        }

    @classmethod
    @transaction.atomic
    def allocate_payment(cls, member, total_amount, payment_method, receipt_reference,
                         payment_date, notes, recorded_by):
        """
        Allocate a dues payment across outstanding years (oldest first),
        then to future years if there's excess.
        Only allocates from join_year onward.
        Returns a dict with: transaction, allocations list, messages list.
        """
        from decimal import Decimal

        total_amount = Decimal(str(total_amount))
        if total_amount <= 0:
            raise ValidationError("Payment amount must be greater than zero.")

        current_year = timezone.now().year
        join_year = cls.get_member_join_year(member)
        start_year = max(join_year, 2020)
        yearly_dues = cls.YEARLY_DUES_AMOUNT

        # Create the transaction record
        transaction_obj = DuesPaymentTransaction.objects.create(
            member=member,
            total_amount=total_amount,
            payment_method=payment_method,
            receipt_reference=receipt_reference or "",
            payment_date=payment_date,
            notes=notes or "",
            recorded_by=recorded_by,
        )

        remaining = total_amount
        allocations = []
        messages_list = []

        # Phase 1: Allocate to outstanding years (oldest first), starting from join year
        for year in range(start_year, current_year + 1):
            if remaining <= 0:
                break

            dp, created = cls.objects.get_or_create(
                member=member,
                year=year,
                defaults={
                    "amount_paid": Decimal("0"),
                    "notes": "",
                    "recorded_by": recorded_by,
                },
            )

            needed = yearly_dues - dp.amount_paid
            if needed > 0:
                allocate = min(needed, remaining)
                dp.amount_paid += allocate
                dp.recorded_by = recorded_by  # Update to latest recorder
                if notes:
                    dp.notes = notes if not dp.notes else f"{dp.notes}; {notes}"
                dp.save()
                dp.transactions.add(transaction_obj)

                # Create/update linked Income record
                if dp.income:
                    dp.income.amount = dp.amount_paid
                    dp.income.reason = f"Yearly Dues — {year}"
                    dp.income.paid_by = member.get_full_name()
                    dp.income.member = member  # Link income to member
                    # Preserve original creator — do NOT overwrite created_by
                    dp.income.save()
                else:
                    income = Income.objects.create(
                        income_type="DUES",
                        amount=dp.amount_paid,
                        reason=f"Yearly Dues — {year}",
                        paid_by=member.get_full_name(),
                        member=member,  # Link income to member
                        created_by=recorded_by,
                    )
                    dp.income = income
                    dp.save(update_fields=["income"])

                remaining -= allocate
                allocations.append({
                    "year": year,
                    "allocated": allocate,
                    "total_paid_for_year": dp.amount_paid,
                    "status": dp.status,
                    "is_new": created,
                })

                if dp.is_fully_paid:
                    messages_list.append(f"Year {year} fully paid (₦{dp.amount_paid:,.2f}).")
                else:
                    messages_list.append(
                        f"Year {year} partially paid (₦{dp.amount_paid:,.2f} of ₦{yearly_dues:,.2f}). "
                        f"Remaining: ₦{dp.remaining_balance:,.2f}."
                    )

        # Phase 2: Allocate remaining to future years (prepaid)
        future_year = current_year + 1
        while remaining > 0:
            dp, created = cls.objects.get_or_create(
                member=member,
                year=future_year,
                defaults={
                    "amount_paid": Decimal("0"),
                    "notes": "",
                    "recorded_by": recorded_by,
                },
            )

            needed = yearly_dues - dp.amount_paid
            if needed > 0:
                allocate = min(needed, remaining)
                dp.amount_paid += allocate
                dp.recorded_by = recorded_by
                if notes:
                    dp.notes = notes if not dp.notes else f"{dp.notes}; {notes}"
                dp.save()
                dp.transactions.add(transaction_obj)

                # Create/update linked Income record
                if dp.income:
                    dp.income.amount = dp.amount_paid
                    dp.income.reason = f"Yearly Dues — {future_year} (Prepaid)"
                    dp.income.paid_by = member.get_full_name()
                    dp.income.member = member  # Link income to member
                    # Preserve original creator — do NOT overwrite created_by
                    dp.income.save()
                else:
                    income = Income.objects.create(
                        income_type="DUES",
                        amount=dp.amount_paid,
                        reason=f"Yearly Dues — {future_year} (Prepaid)",
                        paid_by=member.get_full_name(),
                        member=member,  # Link income to member
                        created_by=recorded_by,
                    )
                    dp.income = income
                    dp.save(update_fields=["income"])

                remaining -= allocate
                allocations.append({
                    "year": future_year,
                    "allocated": allocate,
                    "total_paid_for_year": dp.amount_paid,
                    "status": dp.status,
                    "is_new": created,
                    "is_prepaid": True,
                })

                if dp.is_fully_paid:
                    messages_list.append(
                        f"Year {future_year} prepaid (₦{dp.amount_paid:,.2f}). "
                        f"Will activate automatically when {future_year} begins."
                    )
                else:
                    messages_list.append(
                        f"Year {future_year} partially prepaid (₦{dp.amount_paid:,.2f} of ₦{yearly_dues:,.2f})."
                    )

            future_year += 1

        # Handle any tiny remainder (shouldn't happen with proper amounts)
        if remaining > 0:
            messages_list.append(
                f"Note: ₦{remaining:,.2f} could not be allocated (remainder after full allocations)."
            )

        return {
            "transaction": transaction_obj,
            "allocations": allocations,
            "messages": messages_list,
            "total_allocated": total_amount - remaining,
            "remaining": remaining,
        }


class Expense(BaseModel):
    """Expense model for tracking association expenditures."""

    CATEGORY_CHOICES = [
        ("ADMINISTRATIVE", "Administrative"),
        ("PROJECT", "Project"),
        ("EVENT", "Event"),
        ("MAINTENANCE", "Maintenance"),
        ("SALARY", "Salary"),
        ("OTHER", "Other"),
    ]

    id = models.BigAutoField(primary_key=True)
    amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
        verbose_name="Amount"
    )
    category = models.CharField(
        max_length=50,
        choices=CATEGORY_CHOICES,
        verbose_name="Category"
    )
    description = models.TextField(verbose_name="Description")
    receipt_file = models.FileField(
        upload_to="finance/receipts/%Y/%m/",
        verbose_name="Receipt File"
    )
    created_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        related_name="expenses_created",
        verbose_name="Created By"
    )

    class Meta:
        db_table = "finance_expense"
        verbose_name = "Expense"
        verbose_name_plural = "Expenses"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["category"]),
            models.Index(fields=["created_at"]),
        ]

    def __str__(self):
        return f"₦{self.amount:,.2f} - {self.category}"

    def clean(self):
        if not self.receipt_file:
            raise ValidationError({"receipt_file": "Receipt upload is mandatory."})