"""
Signals for OYA elections.

Automatically applies election results — winner assignment and outgoing
executive removal — the moment an Election's status transitions to
COMPLETED, regardless of what path triggered the change (the edit form,
the admin panel, a management command, etc.), per the "fully automatic"
requirement.
"""
import logging
from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver
from .models import Election

logger = logging.getLogger("oya")


@receiver(pre_save, sender=Election)
def stash_previous_status(sender, instance, **kwargs):
    """Remember the pre-save status so post_save can detect a real transition."""
    if instance.pk:
        try:
            instance._previous_status = Election.objects.only("status").get(pk=instance.pk).status
        except Election.DoesNotExist:
            instance._previous_status = None
    else:
        instance._previous_status = None


@receiver(post_save, sender=Election)
def apply_results_on_completion(sender, instance, created, **kwargs):
    """
    Run process_election_results() exactly once, only on the transition
    INTO COMPLETED — never on a later save of an already-completed
    election (which would otherwise re-run vote counting and create
    duplicate Executive records every time the election is edited again).
    """
    previous_status = getattr(instance, "_previous_status", None)
    if created or previous_status == "COMPLETED" or instance.status != "COMPLETED":
        return

    summary = instance.process_election_results()
    _log_and_notify(instance, summary)


def _log_and_notify(election, summary):
    """Audit-log the outcome and raise a global notification for anything
    that needed manual resolution, so it doesn't happen silently."""
    from auditlogs.services import log_action
    from notifications.models import Notification

    winners = summary["winners"]
    tied_posts = summary["tied_posts"]
    no_votes_posts = summary["no_votes_posts"]
    invalid_post_names = summary["invalid_post_names"]
    errors = summary.get("errors", {})

    winner_lines = [f"{post}: {c.member.full_name}" for post, c in winners.items()]
    description = (
        f"Election '{election.title}' completed. "
        f"Assigned: {'; '.join(winner_lines) if winner_lines else 'none'}."
    )
    if tied_posts:
        description += f" Tied (needs manual resolution): {', '.join(tied_posts)}."
    if no_votes_posts:
        description += f" No votes cast: {', '.join(no_votes_posts)}."
    if invalid_post_names:
        description += f" Unrecognized post name (needs manual resolution): {', '.join(invalid_post_names)}."
    if errors:
        error_summary = "; ".join(f"{post} ({msg})" for post, msg in errors.items())
        description += f" Failed to apply (needs manual resolution): {error_summary}."

    try:
        log_action(
            user=None,
            action="UPDATE",
            object_type="Election",
            object_id=election.id,
            ip_address="",
            description=description,
        )
    except Exception:
        logger.exception("Failed to audit-log election completion for election %s", election.id)

    needs_attention = bool(tied_posts or invalid_post_names or errors)
    try:
        Notification.objects.create(
            title=f"Election completed: {election.title}",
            message=description + (
                " Some posts need manual review in Executives — see the audit log."
                if needs_attention else ""
            ),
            notification_type="ELECTION",
            is_global=True,
        )
    except Exception:
        logger.exception("Failed to create election-completion notification for election %s", election.id)
