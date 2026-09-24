from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('elections', '0002_rename_elections_e_status_idx_elections_e_status_e3ccd0_idx_and_more'),
        ('executives', '0002_alter_executive_post'),
    ]

    operations = [
        migrations.AddField(
            model_name='executive',
            name='elected_via',
            field=models.ForeignKey(
                blank=True,
                help_text=(
                    "The election that produced this executive term. Used to group "
                    "executives into administrations for Executive Handover Reports. "
                    "Left blank for executives who predate this tracking (treated as "
                    "the 'Founding Administration')."
                ),
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='executives_elected',
                to='elections.election',
                verbose_name='Elected Via Election',
            ),
        ),
    ]
