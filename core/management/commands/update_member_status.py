"""
Management command to update member statuses.
Automatically moves members aged 56+ to PAST_MEMBER status.
"""
import logging
from django.core.management.base import BaseCommand
from django.utils import timezone
from members.models import Member
from auditlogs.services import log_action

logger = logging.getLogger("oya")


class Command(BaseCommand):
    help = "Update member statuses - moves members aged 56+ to PAST_MEMBER"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be changed without making changes",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]

        # Find active members aged 56 or older
        members_to_update = Member.objects.filter(
            status="ACTIVE",
            age__gte=56
        )

        count = members_to_update.count()

        if count == 0:
            self.stdout.write(
                self.style.SUCCESS("No members need status update.")
            )
            return

        self.stdout.write(
            f"Found {count} member(s) aged 56+ with ACTIVE status."
        )

        if dry_run:
            self.stdout.write("Dry run - no changes made:")
            for member in members_to_update:
                self.stdout.write(
                    f"  - {member.serial_number}: {member.full_name} "
                    f"(age {member.age}) -> PAST_MEMBER"
                )
            return

        # Update members
        updated = 0
        for member in members_to_update:
            old_status = member.status
            member.status = "PAST_MEMBER"
            member.save(update_fields=["status"])
            updated += 1

            self.stdout.write(
                f"  Updated {member.serial_number}: {member.full_name} "
                f"({old_status} -> PAST_MEMBER)"
            )

            # Log the action
            log_action(
                user=None,
                action="UPDATE",
                object_type="Member",
                object_id=member.id,
                description=(
                    f"Auto-updated: {member.serial_number} moved from "
                    f"{old_status} to PAST_MEMBER (age: {member.age})"
                )
            )

        self.stdout.write(
            self.style.SUCCESS(f"Successfully updated {updated} member(s).")
        )
