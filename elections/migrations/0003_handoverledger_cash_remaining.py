from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('elections', '0002_rename_elections_e_status_idx_elections_e_status_e3ccd0_idx_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='handoverledger',
            name='cash_remaining',
            field=models.DecimalField(
                decimal_places=2,
                default=0.00,
                help_text='Cash physically remaining in hand at handover. Administrator-only field.',
                max_digits=15,
                verbose_name='Cash Remaining',
            ),
        ),
    ]
