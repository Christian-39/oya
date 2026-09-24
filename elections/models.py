"""
Models for OYA elections.
"""
from django.db import models
from django.conf import settings
from django.db.models import Sum, Q, Count
from decimal import Decimal
from core.models import BaseModel


class Election(BaseModel):
    """Election model for managing association elections."""

    STATUS_CHOICES = [
        ("UPCOMING", "Upcoming"),
        ("ONGOING", "Ongoing"),
        ("COMPLETED", "Completed"),
        ("CANCELLED", "Cancelled"),
    ]

    id = models.BigAutoField(primary_key=True)
    title = models.CharField(max_length=255, verbose_name="Title")
    start_date = models.DateTimeField(verbose_name="Start Date")
    end_date = models.DateTimeField(verbose_name="End Date")
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="UPCOMING",
        verbose_name="Status"
    )
    description = models.TextField(blank=True, verbose_name="Description")
    results_applied_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Results Applied At",
        help_text=(
            "Timestamp when process_election_results() ran. This is the "
            "authoritative anchor for this administration's tenure_start in "
            "elections.administrations — independent of any individual "
            "officer's Executive.start_date (which is deliberately left "
            "untouched on re-election, so it can be stale relative to when "
            "this election's results actually took effect) and independent "
            "of the editable start_date/end_date fields above (which are "
            "voting-period fields, not office-holding dates)."
        ),
    )

    class Meta:
        db_table = "elections_election"
        verbose_name = "Election"
        verbose_name_plural = "Elections"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["start_date"]),
        ]

    def __str__(self):
        return self.title

    def process_election_results(self):
        """
        Automatically applied when this election's status transitions to
        COMPLETED (see elections/signals.py):

        - For every post actually contested in this election (i.e. with at
          least one Candidate), the candidate with the highest vote count
          becomes the new current Executive for that post.
        - The previous current holder of that post (if a different member)
          is ended (is_current=False, end_date=today) — i.e. reverted to a
          regular member — UNLESS they also won a different contested post
          in this same election, in which case only their old post ends
          and their new one is created; they are not left without a post.
        - Posts not contested in this election are left completely
          untouched — this is not a "wipe the whole executive body" reset,
          only the posts actually up for election are affected.
        - A tie for the top vote count, or a post with zero votes cast, is
          left for manual resolution rather than guessed automatically.
        - A candidate's post value that doesn't match one of
          Executive.POST_CHOICES is also left for manual resolution,
          rather than silently creating an inconsistent Executive record.

        Returns a summary dict:
            {
                "winners": {post: Candidate, ...},
                "tied_posts": [post, ...],
                "no_votes_posts": [post, ...],
                "invalid_post_names": [post, ...],
                "errors": {post: error_message, ...},
            }
        """
        from django.db import transaction
        from django.utils import timezone
        from executives.models import Executive

        today = timezone.now().date()
        valid_post_values = {choice[0] for choice in Executive.POST_CHOICES}

        contested_posts = list(
            self.candidates.values_list("post", flat=True).distinct()
        )

        winners = {}
        tied_posts = []
        no_votes_posts = []
        invalid_post_names = []
        errors = {}

        for post in contested_posts:
            if post not in valid_post_values:
                invalid_post_names.append(post)
                continue

            candidates = list(
                self.candidates.filter(post=post).select_related("member").order_by("-votes")
            )
            if not candidates:
                continue

            top_votes = candidates[0].votes
            if top_votes <= 0:
                no_votes_posts.append(post)
                continue

            top_candidates = [c for c in candidates if c.votes == top_votes]
            if len(top_candidates) > 1:
                tied_posts.append(post)
                continue

            winner = top_candidates[0]

            try:
                with transaction.atomic():
                    current_holder = Executive.objects.filter(post=post, is_current=True).first()
                    if current_holder and current_holder.member_id == winner.member_id:
                        # Re-elected to the same post they already hold — no new
                        # term record needed, but re-tag them into this election's
                        # administration so handover reports group them correctly.
                        if current_holder.elected_via_id != self.id:
                            current_holder.elected_via = self
                            current_holder.save(update_fields=["elected_via", "updated_at"])
                        winners[post] = winner
                        continue

                    # Outgoing: end the previous holder of this specific post.
                    if current_holder:
                        current_holder.is_current = False
                        current_holder.end_date = today
                        current_holder.save(update_fields=["is_current", "end_date", "updated_at"])

                    # If the winner currently holds a different post, end that
                    # one too — a member holds one executive post at a time.
                    Executive.objects.filter(
                        member=winner.member, is_current=True
                    ).exclude(post=post).update(is_current=False, end_date=today)

                    Executive.objects.create(
                        member=winner.member,
                        post=post,
                        start_date=today,
                        is_current=True,
                        elected_via=self,
                    )
                winners[post] = winner
            except Exception as exc:
                # Isolated per-post: a problem with one post (e.g. a rare
                # unique_together collision on re-election to a previously
                # held, non-consecutive post) must not roll back or block
                # every other post's results.
                errors[post] = str(exc)

        # Stamp the moment results were actually applied — this is the
        # authoritative tenure_start anchor used by
        # elections.administrations._build_administration_base(), since
        # individual Executive.start_date values are NOT reliable for this
        # (a re-elected officer keeps their pre-existing start_date, see
        # above). Safe to save here: this re-save keeps status COMPLETED,
        # so the post_save signal's "previous_status == COMPLETED" guard
        # prevents this from re-triggering result processing.
        self.results_applied_at = timezone.now()
        self.save(update_fields=["results_applied_at", "updated_at"])

        return {
            "winners": winners,
            "tied_posts": tied_posts,
            "no_votes_posts": no_votes_posts,
            "invalid_post_names": invalid_post_names,
            "errors": errors,
        }


class Candidate(BaseModel):
    """Candidate model for election contestants."""

    id = models.BigAutoField(primary_key=True)
    election = models.ForeignKey(
        Election,
        on_delete=models.CASCADE,
        related_name="candidates",
        verbose_name="Election"
    )
    member = models.ForeignKey(
        "members.Member",
        on_delete=models.PROTECT,
        related_name="candidacies",
        verbose_name="Member"
    )
    post = models.CharField(
        max_length=50,
        verbose_name="Post"
    )
    photo = models.ImageField(
        upload_to="elections/candidates/%Y/%m/",
        blank=True,
        null=True,
        verbose_name="Campaign Photo"
    )
    manifesto = models.TextField(blank=True, verbose_name="Manifesto")
    votes = models.PositiveIntegerField(default=0, verbose_name="Votes")

    class Meta:
        db_table = "elections_candidate"
        verbose_name = "Candidate"
        verbose_name_plural = "Candidates"
        ordering = ["-votes", "post"]
        unique_together = [["election", "member", "post"]]

    def __str__(self):
        return f"{self.member.full_name} for {self.post}"


class Vote(BaseModel):
    """Vote model to track individual votes per post."""

    id = models.BigAutoField(primary_key=True)
    election = models.ForeignKey(
        Election,
        on_delete=models.CASCADE,
        related_name="vote_records",
        verbose_name="Election"
    )
    candidate = models.ForeignKey(
        Candidate,
        on_delete=models.CASCADE,
        related_name="vote_records",
        verbose_name="Candidate"
    )
    voter = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="election_votes",
        verbose_name="Voter"
    )
    post = models.CharField(
        max_length=50,
        verbose_name="Post"
    )

    class Meta:
        db_table = "elections_vote"
        verbose_name = "Vote"
        verbose_name_plural = "Votes"
        ordering = ["-created_at"]
        unique_together = [["voter", "election", "post"]]

    def __str__(self):
        return f"{self.voter} voted {self.candidate.member.full_name} for {self.post}"


class HandoverLedger(BaseModel):
    """Comprehensive handover ledger for documenting executive transitions."""

    id = models.BigAutoField(primary_key=True)
    election = models.ForeignKey(
        Election,
        on_delete=models.PROTECT,
        related_name="handovers",
        verbose_name="Related Election",
        blank=True,
        null=True,
        help_text="The election that resulted in this executive transition."
    )
    executive = models.ForeignKey(
        "executives.Executive",
        on_delete=models.PROTECT,
        related_name="handovers",
        verbose_name="Outgoing Executive"
    )

    # Tenure period for auto-calculation — nullable for backward-compatible migration
    tenure_start = models.DateField(
        verbose_name="Tenure Start Date",
        help_text="Start date of this executive's tenure (for auto-calculating aggregates).",
        null=True,
        blank=True,
    )
    tenure_end = models.DateField(
        verbose_name="Tenure End Date",
        help_text="End/handover date for this executive's tenure.",
        null=True,
        blank=True,
    )

    # Physical balances being handed over
    # Deprecated: superseded by cash_remaining ("Physical Cash at Hand"),
    # the single manual balance figure on this ledger. Kept only so
    # historical records entered before that reform aren't lost; no longer
    # exposed on HandoverLedgerForm.
    bank_balance = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal("0.00"),
        verbose_name="Bank Balance (Legacy)",
        help_text="Deprecated — superseded by Physical Cash at Hand. Retained for historical records only."
    )
    cash_balance = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal("0.00"),
        verbose_name="Cash Balance (Legacy)",
        help_text="Deprecated — superseded by Physical Cash at Hand. Retained for historical records only."
    )

    # Finance aggregates (auto-calculated during save)
    total_income = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal("0.00"),
        verbose_name="Other Income (Contributions)",
        help_text="All non-dues, non-donation, non-case-fine income recorded during the tenure period. Auto-calculated."
    )
    total_dues = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal("0.00"),
        verbose_name="Yearly Dues Collected",
        help_text="Dues payments recorded during the tenure period. Auto-calculated."
    )
    total_donations = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal("0.00"),
        verbose_name="Total Project Donations",
        help_text="Confirmed project donations received during the tenure period. Auto-calculated."
    )
    taskforce_revenue = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal("0.00"),
        verbose_name="Case Fines Revenue",
        help_text="Fines from resolved case files during the tenure period. Auto-calculated."
    )
    total_expenses = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal("0.00"),
        verbose_name="Total Expenses",
        help_text="Expenses recorded during the tenure period. Auto-calculated."
    )

    # Operations aggregates
    taskforce_total = models.PositiveIntegerField(default=0, verbose_name="Taskforce Total")
    taskforce_active = models.PositiveIntegerField(default=0, verbose_name="Taskforce Active")
    taskforce_inactive = models.PositiveIntegerField(default=0, verbose_name="Taskforce Inactive")

    motorcycle_total = models.PositiveIntegerField(default=0, verbose_name="Motorcycles Total")
    motorcycle_excellent = models.PositiveIntegerField(default=0, verbose_name="Motorcycles Excellent")
    motorcycle_needs_service = models.PositiveIntegerField(default=0, verbose_name="Motorcycles Needs Service")
    motorcycle_grounded = models.PositiveIntegerField(default=0, verbose_name="Motorcycles Grounded")
    motorcycle_acquired = models.PositiveIntegerField(
        default=0, verbose_name="Motorcycles Acquired",
        help_text="Motorcycles acquired during the tenure period. Auto-calculated."
    )

    cases_total = models.PositiveIntegerField(default=0, verbose_name="Cases Handled")
    cases_open = models.PositiveIntegerField(default=0, verbose_name="Cases Open (Unattended)")
    cases_in_progress = models.PositiveIntegerField(default=0, verbose_name="Cases In Progress (Ongoing)")
    cases_resolved = models.PositiveIntegerField(default=0, verbose_name="Cases Resolved")

    # Projects aggregates
    projects_created = models.PositiveIntegerField(
        default=0, verbose_name="Projects Created",
        help_text="Projects created during the tenure period. Auto-calculated."
    )
    projects_completed = models.PositiveIntegerField(default=0, verbose_name="Projects Completed")
    projects_at_hand = models.PositiveIntegerField(
        default=0, verbose_name="Projects In Progress / Handed Over"
    )
    projects_future = models.PositiveIntegerField(default=0, verbose_name="Projects Future/Planned")

    # Pledges aggregates
    pledges_made = models.PositiveIntegerField(
        default=0, verbose_name="Pledges Made This Tenure",
        help_text="Pledges (money, material, or labour) made during the tenure period. Auto-calculated."
    )
    pledge_total_value = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal("0.00"),
        verbose_name="Total Pledge Value",
        help_text="Total pledged value of Money pledges made during the tenure period. Auto-calculated."
    )

    assets_description = models.TextField(
        blank=True,
        verbose_name="Assets Description"
    )
    notes = models.TextField(blank=True, verbose_name="Notes")

    # The ONLY manual figure on the entire ledger. Defaults to ₦0.00 and is
    # only ever edited by an administrator (enforced in HandoverLedgerForm
    # / elections.views) — everyone else sees it read-only. Every other
    # number on this record is recalculated automatically from existing
    # records — see recalculate_aggregates().
    cash_remaining = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal("0.00"),
        verbose_name="Physical Cash at Hand",
        help_text="Cash physically counted and held at handover. The only figure on this ledger entered by hand. Administrator-only field.",
    )

    class Meta:
        db_table = "elections_handoverledger"
        verbose_name = "Handover Ledger"
        verbose_name_plural = "Handover Ledgers"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Handover - {self.executive}"

    @property
    def total_balance(self):
        """Physical balance being handed over. bank_balance/cash_balance are
        deprecated legacy fields (kept only so historical records entered
        before this reform aren't lost) — cash_remaining ("Physical Cash
        at Hand") is the only balance entered by hand going forward."""
        return Decimal(str(self.bank_balance or 0)) + Decimal(str(self.cash_balance or 0)) + Decimal(str(self.cash_remaining or 0))

    @property
    def closing_balance(self):
        """Alias of total_balance — the administration's closing balance."""
        return self.total_balance

    @property
    def net_financial_position(self):
        """Net position: all revenue - expenses + physical balance."""
        return (
            Decimal(str(self.total_income or 0)) +
            Decimal(str(self.total_dues or 0)) +
            Decimal(str(self.total_donations or 0)) +
            Decimal(str(self.taskforce_revenue or 0)) -
            Decimal(str(self.total_expenses or 0)) +
            self.total_balance
        )

    @property
    def net_balance(self):
        """Net Balance: total revenue minus total expenses (excludes the
        physical cash-at-hand figure) — alias matching the Executive
        Handover Report's own terminology."""
        return self.total_revenue - self.total_expenses

    @property
    def total_revenue(self):
        """Total revenue realized during tenure."""
        return (
            Decimal(str(self.total_income or 0)) +
            Decimal(str(self.total_dues or 0)) +
            Decimal(str(self.total_donations or 0)) +
            Decimal(str(self.taskforce_revenue or 0))
        )

    def recalculate_aggregates(self):
        """
        Recalculate every auto-aggregated figure on this ledger from
        existing records — the only manual figure left is cash_remaining
        ("Physical Cash at Hand").

        Tenure dates are derived automatically from the outgoing
        executive's own record (never entered by hand) so this always
        reports exactly that executive's time in office. All the actual
        counting/summing is delegated to elections.administrations — the
        same calculation engine that powers the Executive Handover Report
        — so the two never disagree and nothing is calculated twice.
        """
        from elections.administrations import (
            _finance_section, _projects_section, _cases_section,
            _pledges_section, _motorcycles_section, _taskforce_section,
        )
        from django.utils import timezone

        # Tenure dates are derived, not entered — the outgoing executive's
        # own start_date/end_date is the single source of truth (matches
        # how elections.administrations bounds every other administration's
        # report window).
        if self.executive_id:
            if not self.tenure_start:
                self.tenure_start = self.executive.start_date
            if not self.tenure_end:
                self.tenure_end = self.executive.end_date or timezone.now().date()

        # Guard: nothing to calculate without a resolvable tenure window.
        if not self.tenure_start or not self.tenure_end:
            return

        start, end = self.tenure_start, self.tenure_end
        if start > end:
            start, end = end, start

        # ─── FINANCE ───
        finance = _finance_section(start, end)
        self.total_income = Decimal(str(finance.get("total_income", 0) or 0))
        self.total_dues = Decimal(str(finance.get("total_dues", 0) or 0))
        self.total_donations = Decimal(str(finance.get("total_donations", 0) or 0))
        self.taskforce_revenue = Decimal(str(finance.get("taskforce_revenue", 0) or 0))
        self.total_expenses = Decimal(str(finance.get("total_expenses", 0) or 0))

        # ─── PROJECTS ───
        projects = _projects_section(start, end, limit=1)
        self.projects_created = projects["counts"]["created"]
        self.projects_completed = projects["counts"]["completed"]
        self.projects_at_hand = projects["counts"]["at_hand"]
        self.projects_future = projects["counts"]["future"]

        # ─── CASES ───
        cases = _cases_section(start, end, limit=1)
        self.cases_total = cases["counts"]["handled"]
        self.cases_open = cases["counts"]["open"]
        self.cases_in_progress = cases["counts"]["in_progress"]
        self.cases_resolved = cases["counts"]["resolved"]

        # ─── PLEDGES ───
        pledges = _pledges_section(start, end, limit=1)
        self.pledges_made = pledges["counts"]["created_in_tenure"]
        self.pledge_total_value = Decimal(str(pledges.get("total_pledged_value", 0) or 0))

        # ─── TASK FORCE ───
        taskforce = _taskforce_section(start, end, limit=1)
        self.taskforce_total = taskforce["counts"]["total"]
        self.taskforce_active = taskforce["counts"]["active"]
        self.taskforce_inactive = taskforce["counts"]["inactive"]

        # ─── MOTORCYCLES / ASSETS ───
        motorcycles = _motorcycles_section(start, end, limit=1)
        self.motorcycle_total = motorcycles["counts"]["total"]
        self.motorcycle_excellent = motorcycles["counts"]["excellent"]
        self.motorcycle_needs_service = motorcycles["counts"]["needs_service"]
        self.motorcycle_grounded = motorcycles["counts"]["grounded"]
        self.motorcycle_acquired = motorcycles["counts"]["acquired"]
