"""
Add Election.results_applied_at — the authoritative tenure_start anchor
used by elections.administrations, decoupled from Executive.start_date
(which is deliberately left unchanged on re-election).

Rename this file to match your app's next migration number, e.g.:
    elections/migrations/0013_election_results_applied_at.py
(check your `elections/migrations/` folder for the current highest number
and adjust `dependencies` below accordingly.)
"""
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("elections", "0005_backfill_new_ledger_aggregates"),
    ]

    operations = [
        migrations.AddField(
            model_name="election",
            name="results_applied_at",
            field=models.DateTimeField(
                blank=True,
                null=True,
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
            ),
        ),
    ]