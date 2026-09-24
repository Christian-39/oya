"""
Cross-app signals for OYA Project Donations.
"""
import logging
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

from .models import Donation, Pledge, PledgePayment

logger = logging.getLogger("oya")


@receiver(post_save, sender=Donation)
def sync_donation_to_finance(sender, instance, created, **kwargs):
    """
    Auto-maintain a linked Income record for confirmed donations.
    - Money donations always sync to finance (existing behaviour).
    - Material donations sync ONLY when update_treasury is enabled, using
      estimated_value as the income amount (Feature 5/8).
    - Labour donations never touch treasury.
    Removes the Income if the donation is cancelled, zeroed out, or the
    type/flag no longer qualifies. A donation still at "Pledge" status
    never touches treasury either — nothing has actually been received yet.
    """
    should_sync = False
    income_amount = None

    if instance.status == "CONFIRMED":
        if instance.donation_type == "MONEY" and instance.amount and instance.amount > 0:
            should_sync = True
            income_amount = instance.amount
        elif instance.donation_type == "MATERIAL" and instance.update_treasury and instance.estimated_value and instance.estimated_value > 0:
            should_sync = True
            income_amount = instance.estimated_value

    if should_sync:
        _ensure_donation_income(instance, income_amount)
    else:
        _remove_donation_income(instance)

    instance.project.update_fundraising_stats()


@receiver(post_delete, sender=Donation)
def cleanup_donation_finance(sender, instance, **kwargs):
    """Delete the linked Income record when a donation is permanently deleted."""
    if instance.income_id:
        try:
            instance.income.delete()
        except Exception:
            pass
    try:
        instance.project.update_fundraising_stats()
    except Exception:
        # Project itself may have been deleted (cascade); nothing to update.
        pass


def _ensure_donation_income(donation, income_amount):
    """Create or update the finance Income record for a donation."""
    from finance.models import Income

    # Resolve payer text and (if possible) the linked User for finance.member
    payer_name = "Anonymous"
    member_user = None

    if donation.donor_type == "MEMBER" and donation.member:
        payer_name = donation.member.full_name
        # Adjust this if your Member model links to User differently
        member_user = getattr(donation.member, "user", None)
    elif donation.donor_type == "OUTSIDE" and donation.outside_donor:
        payer_name = donation.outside_donor.full_name

    reason = f"Project Donation — {donation.project.title}"
    if donation.donation_type == "MATERIAL":
        reason = f"Project Donation (Material: {donation.material_name}) — {donation.project.title}"

    if donation.income:
        # Update existing income
        donation.income.amount = income_amount
        donation.income.reason = reason
        donation.income.paid_by = payer_name
        donation.income.income_type = "PROJECT_DONATION"
        if member_user:
            donation.income.member = member_user
        donation.income.save()
    else:
        # Create new income and link back without re-firing signals
        income = Income.objects.create(
            income_type="PROJECT_DONATION",
            amount=income_amount,
            reason=reason,
            paid_by=payer_name,
            member=member_user,
            created_by=donation.recorded_by,
        )
        Donation.objects.filter(pk=donation.pk).update(income=income)


def _remove_donation_income(donation):
    """Unlink and delete the finance Income record."""
    if donation.income_id:
        income = donation.income
        Donation.objects.filter(pk=donation.pk).update(income=None)
        try:
            income.delete()
        except Exception:
            pass

# ═══════════════════════════════════════════════════════════════
# PLEDGE PAYMENT → TREASURY INTEGRATION (Feature 8)
# ═══════════════════════════════════════════════════════════════

@receiver(post_save, sender=PledgePayment)
def sync_pledge_payment(sender, instance, created, **kwargs):
    """
    Whenever a pledge payment is saved: mirror it as a confirmed Money
    Donation (which drives the existing treasury/Income sync above),
    recompute the pledge's paid/outstanding/status, and refresh the
    project's fundraising totals. One Donation per PledgePayment
    (OneToOneField) prevents duplicate accounting on repeated saves.
    """
    _ensure_pledge_payment_donation(instance)
    instance.pledge.recalculate_status()


@receiver(post_delete, sender=PledgePayment)
def cleanup_pledge_payment(sender, instance, **kwargs):
    """Remove the mirrored Donation (and therefore its Income) when a pledge payment is deleted."""
    if instance.donation_id:
        try:
            instance.donation.delete()
        except Exception:
            pass
    try:
        instance.pledge.recalculate_status()
    except Exception:
        pass


def _ensure_pledge_payment_donation(payment):
    """Create or update the mirrored Donation record for a pledge payment."""
    narration = f"Pledge payment — {payment.pledge.project.title} (Pledge #{payment.pledge_id})"

    if payment.donation_id:
        donation = payment.donation
        donation.amount = payment.amount
        donation.donation_date = payment.payment_date
        donation.payment_method = payment.payment_method
        donation.reference_number = payment.reference_number
        donation.narration = narration
        donation.recorded_by = payment.recorded_by or donation.recorded_by
        donation.save()
    else:
        donation = Donation.objects.create(
            project=payment.pledge.project,
            donor_type="MEMBER",
            member=payment.pledge.member,
            donation_type="MONEY",
            amount=payment.amount,
            payment_method=payment.payment_method,
            reference_number=payment.reference_number,
            narration=narration,
            recorded_by=payment.recorded_by,
            donation_date=payment.payment_date,
            status="CONFIRMED",
        )
        PledgePayment.objects.filter(pk=payment.pk).update(donation=donation)


# ═══════════════════════════════════════════════════════════════
# PROJECT DONATIONS ↔ PLEDGES INTEGRATION
# ═══════════════════════════════════════════════════════════════
#
# A Donation saved with status="Pledge" (any contribution type — money,
# material, or labour) automatically gets a mirrored Pledge record, so the
# donor doesn't have to be entered twice and the pledge immediately shows
# up in the Pledges module. When that same Donation is later fulfilled
# (status -> Confirmed) or withdrawn (status -> Cancelled), the linked
# Pledge is updated to match automatically, and vice versa — marking the
# Pledge Completed/Cancelled directly also updates the Donation. One
# Pledge per Donation (OneToOneField via Donation.pledge) keeps this a
# single source of truth, the same pattern used for PledgePayment <-> 
# Donation above.

_PLEDGE_MIRROR_FIELDS = (
    "donor_type", "member_id", "outside_donor_id", "project_id", "donation_type",
    "material_name", "quantity", "labour_type", "number_of_days", "estimated_value",
)


@receiver(post_save, sender=Donation)
def sync_donation_pledge(sender, instance, created, **kwargs):
    """Keep a Donation with status="Pledge" and its mirrored Pledge record
    in sync in both directions."""
    if instance.status == "PLEDGE":
        _ensure_donation_pledge(instance)
        return

    if not instance.pledge_id:
        return

    target_status = {"CONFIRMED": "COMPLETED", "CANCELLED": "CANCELLED"}.get(instance.status)
    if target_status and instance.pledge.status != target_status:
        Pledge.objects.filter(pk=instance.pledge_id).update(status=target_status)


@receiver(post_delete, sender=Donation)
def cleanup_donation_pledge(sender, instance, **kwargs):
    """Remove the mirrored Pledge when its originating Donation is deleted —
    it only ever existed to represent this donation in the Pledges module."""
    if instance.pledge_id:
        try:
            instance.pledge.delete()
        except Exception:
            pass


@receiver(post_save, sender=Pledge)
def sync_pledge_donation(sender, instance, created, **kwargs):
    """Reverse direction: fulfilling/cancelling a Pledge from the Pledges
    module (for a pledge that originated from a Donation) updates that
    Donation to match, so both modules always agree without double entry.
    Goes through donation.save() (not a bare .update()) so the existing
    treasury signal (sync_donation_to_finance) still fires and creates/
    updates the Income record when a pledge is fulfilled this way. This
    can't loop forever: sync_donation_pledge's own equality check on the
    way back finds the Pledge already at the target status and stops."""
    try:
        donation = instance.source_donation
    except Donation.DoesNotExist:
        return

    target_status = {"COMPLETED": "CONFIRMED", "CANCELLED": "CANCELLED"}.get(instance.status)
    if target_status and donation.status != target_status:
        donation.status = target_status
        donation.save(update_fields=["status", "updated_at"])


def _ensure_donation_pledge(donation):
    """Create or update the mirrored Pledge record for a Pledge-status donation."""
    field_values = {
        "donor_type": donation.donor_type,
        "member_id": donation.member_id,
        "outside_donor_id": donation.outside_donor_id,
        "project_id": donation.project_id,
        "donation_type": donation.donation_type,
        "pledged_amount": donation.amount,
        "material_name": donation.material_name,
        "quantity": donation.quantity,
        "labour_type": donation.labour_type,
        "number_of_days": donation.number_of_days,
        "estimated_value": donation.estimated_value,
        "notes": donation.narration,
        "created_by_id": donation.recorded_by_id,
    }

    if donation.pledge_id:
        Pledge.objects.filter(pk=donation.pledge_id).update(**field_values)
    else:
        pledge = Pledge.objects.create(status="PENDING", **field_values)
        Donation.objects.filter(pk=donation.pk).update(pledge=pledge)
