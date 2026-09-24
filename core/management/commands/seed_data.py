"""
Management command to seed the database with initial data.
"""
import logging
import random
from datetime import date, timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.contrib.auth.hashers import make_password
from accounts.models import User
from members.models import Clan, Member
from executives.models import Executive
from operations.models import Motorcycle, CaseFile, TaskForceMember
from notifications.models import Notification
from auditlogs.models import AuditLog
from elections.models import Election, Candidate
from finance.models import Income, Expense
from projects.models import Project
from settingsapp.models import SystemSettings

logger = logging.getLogger("oya")

NIGERIAN_STATES = [
    "Abia", "Adamawa", "Akwa Ibom", "Anambra", "Bauchi", "Bayelsa",
    "Benue", "Borno", "Cross River", "Delta", "Ebonyi", "Edo",
    "Ekiti", "Enugu", "FCT", "Gombe", "Imo", "Jigawa", "Kaduna",
    "Kano", "Katsina", "Kebbi", "Kogi", "Kwara", "Lagos", "Nasarawa",
    "Niger", "Ogun", "Ondo", "Osun", "Oyo", "Plateau", "Rivers",
    "Sokoto", "Taraba", "Yobe", "Zamfara"
]

CLAN_NAMES = [
    "Umu Onoja", "Umu Osede", "Umu Edoga",
    "Umu Nna Ose", "Umu Igwurube", "Others"
]

SAMPLE_MEMBERS = [
    {
        "serial_number": "OYA-2026-0001",
        "full_name": "Chinedu Okonkwo",
        "phone": "08031234567",
        "age": 45,
        "state_or_abroad": "Enugu",
    },
    {
        "serial_number": "OYA-2026-0002",
        "full_name": "Emeka Okafor",
        "phone": "08032345678",
        "age": 38,
        "state_or_abroad": "Lagos",
    },
    {
        "serial_number": "OYA-2026-0003",
        "full_name": "Obinna Nwosu",
        "phone": "08033456789",
        "age": 52,
        "state_or_abroad": "Abia",
    },
    {
        "serial_number": "OYA-2026-0004",
        "full_name": "Ifeanyi Eze",
        "phone": "08034567890",
        "age": 29,
        "state_or_abroad": "Imo",
    },
    {
        "serial_number": "OYA-2026-0005",
        "full_name": "Uchenna Ibe",
        "phone": "08035678901",
        "age": 41,
        "state_or_abroad": "Anambra",
    },
]

EXECUTIVE_POSTS = [
    "President", "Deputy President", "Secretary", "Assistant Secretary",
    "Treasurer", "Financial Secretary", "Assistant Financial Secretary",
    "PRO", "Assistant PRO", "DOS", "Assistant DOS",
    "Auditor 1", "Auditor 2", "Provost 1", "Provost 2", "Provost 3"
]


class Command(BaseCommand):
    help = "Seed the database with initial data"

    def add_arguments(self, parser):
        parser.add_argument(
            "--flush",
            action="store_true",
            help="Delete existing data before seeding",
        )

    def handle(self, *args, **options):
        if options["flush"]:
            self.stdout.write("Flushing existing data...")
            self._flush_data()

        self.stdout.write("Seeding data...")

        self._seed_system_settings()
        self._seed_clans()
        self._seed_members()
        self._seed_executives()
        self._seed_motorcycles()
        self._seed_cases()
        self._seed_elections()
        self._seed_finance()
        self._seed_projects()
        self._seed_notifications()
        self._seed_audit_logs()

        self.stdout.write(self.style.SUCCESS("Data seeding complete!"))

    def _flush_data(self):
        """Remove existing seeded data."""
        AuditLog.objects.all().delete()
        Notification.objects.all().delete()
        Candidate.objects.all().delete()
        Election.objects.all().delete()
        HandoverLedger = __import__("elections.models", fromlist=["HandoverLedger"]).HandoverLedger
        HandoverLedger.objects.all().delete()
        Expense.objects.all().delete()
        Income.objects.all().delete()
        Project.objects.all().delete()
        CaseFile.objects.all().delete()
        Motorcycle.objects.all().delete()
        TaskForceMember.objects.all().delete()
        Executive.objects.all().delete()
        Member.objects.all().delete()
        Clan.objects.all().delete()
        User.objects.filter(serial_number__startswith="OYA-").delete()

    def _seed_system_settings(self):
        """Create system settings."""
        settings, created = SystemSettings.objects.get_or_create(pk=1)
        if created:
            self.stdout.write("  Created system settings")
        else:
            self.stdout.write("  System settings already exist")

    def _seed_clans(self):
        """Seed clan data."""
        for name in CLAN_NAMES:
            Clan.objects.get_or_create(name=name)
        self.stdout.write(f"  Seeded {len(CLAN_NAMES)} clans")

    def _seed_members(self):
        """Seed sample members."""
        clans = list(Clan.objects.all())

        for i, data in enumerate(SAMPLE_MEMBERS):
            clan = clans[i % len(clans)] if clans else None
            Member.objects.get_or_create(
                serial_number=data["serial_number"],
                defaults={
                    "full_name": data["full_name"],
                    "phone": data["phone"],
                    "age": data["age"],
                    "umu_nna_clan": clan,
                    "state_or_abroad": data["state_or_abroad"],
                    "status": "ACTIVE",
                }
            )

        self.stdout.write(f"  Seeded {len(SAMPLE_MEMBERS)} members")

    def _seed_executives(self):
        """Seed executive roster."""
        members = list(Member.objects.filter(status="ACTIVE"))
        if not members:
            self.stdout.write("  No members found for executives")
            return

        for i, post in enumerate(EXECUTIVE_POSTS):
            member = members[i % len(members)]
            Executive.objects.get_or_create(
                member=member,
                post=post,
                is_current=True,
                defaults={
                    "start_date": date(2026, 1, 1),
                }
            )

        self.stdout.write(f"  Seeded {len(EXECUTIVE_POSTS)} executives")

    def _seed_motorcycles(self):
        """Seed motorcycle data."""
        motorcycles_data = [
            {"asset_tag": "OYA-MC-001", "brand": "Honda", "model": "CG125", "year": 2024, "condition": "EXCELLENT"},
            {"asset_tag": "OYA-MC-002", "brand": "Yamaha", "model": "YBR125", "year": 2023, "condition": "NEEDS_SERVICE"},
            {"asset_tag": "OYA-MC-003", "brand": "Suzuki", "model": "GN125", "year": 2022, "condition": "EXCELLENT"},
        ]

        members = list(Member.objects.filter(status="ACTIVE"))

        for i, data in enumerate(motorcycles_data):
            defaults = {k: v for k, v in data.items() if k != "asset_tag"}
            if members:
                defaults["assigned_to"] = members[i % len(members)]
            Motorcycle.objects.get_or_create(
                asset_tag=data["asset_tag"],
                defaults=defaults
            )

        self.stdout.write(f"  Seeded {len(motorcycles_data)} motorcycles")

    def _seed_cases(self):
        """Seed case files."""
        members = list(Member.objects.filter(status="ACTIVE"))
        if not members:
            return

        cases_data = [
            {
                "case_number": "CASE-2026-001",
                "title": "Unauthorized Absence",
                "description": "Member failed to attend three consecutive meetings without prior notice.",
                "fine_amount": 5000.00,
                "status": "OPEN",
                "respondent": members[0] if members else None,
            },
            {
                "case_number": "CASE-2026-002",
                "title": "Late Dues Payment",
                "description": "Member has not paid yearly dues for the current financial year.",
                "fine_amount": 2000.00,
                "status": "IN_PROGRESS",
                "respondent": members[1] if len(members) > 1 else None,
            },
        ]

        for data in cases_data:
            CaseFile.objects.get_or_create(
                case_number=data["case_number"],
                defaults=data
            )

        self.stdout.write(f"  Seeded {len(cases_data)} cases")

    def _seed_elections(self):
        """Seed election data."""
        election, created = Election.objects.get_or_create(
            title="OYA General Election 2026",
            defaults={
                "start_date": timezone.now() + timedelta(days=30),
                "end_date": timezone.now() + timedelta(days=37),
                "status": "UPCOMING",
                "description": "Quadrennial general election for executive positions.",
            }
        )
        self.stdout.write("  Seeded election data")

    def _seed_finance(self):
        """Seed finance data."""
        income_data = [
            {"amount": 50000.00, "reason": "Annual Dues Collection", "paid_by": "Members"},
            {"amount": 25000.00, "reason": "Donation from Patron", "paid_by": "Chief Okafor"},
            {"amount": 15000.00, "reason": "Fundraising Event", "paid_by": "Event Proceeds"},
        ]

        for data in income_data:
            Income.objects.get_or_create(
                reason=data["reason"],
                defaults={
                    "amount": data["amount"],
                    "paid_by": data["paid_by"],
                }
            )

        self.stdout.write(f"  Seeded {len(income_data)} income records")

    def _seed_projects(self):
        """Seed project data."""
        projects_data = [
            {
                "title": "Community Hall Renovation",
                "budget": 500000.00,
                "status": "AT_HAND",
                "progress_percentage": 35,
                "description": "Renovation of the Okpo Community Hall.",
            },
            {
                "title": "Youth Skills Training",
                "budget": 200000.00,
                "status": "FUTURE",
                "progress_percentage": 0,
                "description": "Skills acquisition program for youths.",
            },
            {
                "title": "Road Maintenance",
                "budget": 350000.00,
                "status": "FINISHED",
                "progress_percentage": 100,
                "description": "Maintenance of access roads.",
            },
        ]

        for data in projects_data:
            Project.objects.get_or_create(
                title=data["title"],
                defaults=data
            )

        self.stdout.write(f"  Seeded {len(projects_data)} projects")

    def _seed_notifications(self):
        """Seed notification data."""
        notification_types = ["INFO", "SUCCESS", "WARNING", "ELECTION", "FINANCE", "PROJECT"]
        titles = [
            "Welcome to OYA System",
            "Executive Meeting Scheduled",
            "Dues Payment Reminder",
            "Election Nomination Open",
            "Project Update Available",
            "New Member Registration",
            "Annual General Meeting",
            "Financial Report Ready",
            "Task Force Assignment",
            "System Maintenance Notice",
        ]

        for i, title in enumerate(titles):
            Notification.objects.get_or_create(
                title=title,
                defaults={
                    "message": f"This is a sample notification: {title}. Please check the details.",
                    "notification_type": notification_types[i % len(notification_types)],
                    "is_global": True,
                }
            )

        self.stdout.write(f"  Seeded {len(titles)} notifications")

    def _seed_audit_logs(self):
        """Seed audit log data."""
        actions = ["CREATE", "UPDATE", "DELETE", "LOGIN", "PIN_RESET"]
        object_types = ["Member", "User", "Executive", "Finance", "Project", "CaseFile"]
        descriptions = [
            "Created new member record",
            "Updated user profile",
            "Deleted expired record",
            "User login attempt",
            "PIN reset performed",
            "Executive post assigned",
            "Income recorded",
            "Project status updated",
            "Case file created",
            "Notification sent",
        ]

        for i in range(20):
            AuditLog.objects.create(
                action=actions[i % len(actions)],
                object_type=object_types[i % len(object_types)],
                object_id=i + 1,
                description=descriptions[i % len(descriptions)],
                ip_address=f"192.168.1.{(i % 255) + 1}",
            )

        self.stdout.write("  Seeded 20 audit logs")
