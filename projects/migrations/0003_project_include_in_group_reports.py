# Generated manually (no network access to run makemigrations in this
# environment) — follows the same style Django would produce for this
# model change. Verify with `python manage.py makemigrations --check`
# before applying in your environment.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('projects', '0002_project_enable_fundraising_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='project',
            name='include_in_group_reports',
            field=models.BooleanField(
                default=True,
                help_text=(
                    "If disabled, this project's donations are excluded from donation "
                    "group reports only. Treasury, finance, and project totals are "
                    "unaffected and donation records remain intact."
                ),
                verbose_name='Include in Donation Group Reports?',
            ),
        ),
        migrations.AddIndex(
            model_name='project',
            index=models.Index(fields=['include_in_group_reports'], name='projects_incl_grprpt_idx'),
        ),
    ]
