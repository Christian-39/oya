from django.db import migrations


def backfill_aggregates(apps, schema_editor):
    """Recalculate every existing HandoverLedger record with the new
    (reformed) auto-calculation engine, so pre-existing records get real
    values for the newly-added fields (projects_created, pledges_made,
    pledge_total_value, motorcycle_acquired) instead of sitting at 0.

    Uses the real HandoverLedger model (not the historical migration-state
    model) because recalculate_aggregates() delegates to the live
    elections.administrations calculation engine — reimplementing that
    logic against frozen historical models would duplicate it, which is
    exactly what this reform is trying to avoid.
    """
    from elections.models import HandoverLedger

    for ledger in HandoverLedger.objects.select_related("executive").all():
        ledger.recalculate_aggregates()
        ledger.save()


def noop_reverse(apps, schema_editor):
    """No reverse action — the recalculated values are strictly additive
    (fixes previously-zero/incorrect figures) and safe to leave in place."""
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('elections', '0004_handoverledger_auto_calculated_reform'),
    ]

    operations = [
        migrations.RunPython(backfill_aggregates, noop_reverse),
    ]
