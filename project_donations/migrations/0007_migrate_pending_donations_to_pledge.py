# Generated manually (no network access to run makemigrations in this
# environment). Renames the on-disk status value for existing donations —
# no data is lost, only the stored string changes to match the new
# STATUS_CHOICES introduced in 0006 (Pending -> Pledge).

from django.db import migrations


def rename_pending_to_pledge(apps, schema_editor):
    Donation = apps.get_model('project_donations', 'Donation')
    Pledge = apps.get_model('project_donations', 'Pledge')

    donations = Donation.objects.filter(status='PENDING')
    donations.update(status='PLEDGE')

    # Backfill a linked Pledge for each migrated donation so historical
    # "Pending" donations retroactively appear in the Pledges module too,
    # same as newly-created Pledge-status donations do going forward.
    for donation in donations:
        if donation.pledge_id:
            continue
        pledge = Pledge.objects.create(
            donor_type=donation.donor_type,
            member_id=donation.member_id,
            outside_donor_id=donation.outside_donor_id,
            project_id=donation.project_id,
            donation_type=donation.donation_type,
            pledged_amount=donation.amount,
            material_name=donation.material_name,
            quantity=donation.quantity,
            labour_type=donation.labour_type,
            number_of_days=donation.number_of_days,
            estimated_value=donation.estimated_value,
            notes=donation.narration,
            created_by_id=donation.recorded_by_id,
            status='PENDING',
        )
        donation.pledge_id = pledge.id
        donation.save(update_fields=['pledge'])


def rename_pledge_to_pending(apps, schema_editor):
    """Reverse migration, for completeness."""
    Donation = apps.get_model('project_donations', 'Donation')
    Donation.objects.filter(status='PLEDGE').update(status='PENDING')


class Migration(migrations.Migration):

    dependencies = [
        ('project_donations', '0006_donation_pledge_and_pledge_types'),
    ]

    operations = [
        migrations.RunPython(rename_pending_to_pledge, rename_pledge_to_pending),
    ]
