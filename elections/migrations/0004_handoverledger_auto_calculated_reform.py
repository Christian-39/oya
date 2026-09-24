from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('elections', '0003_handoverledger_cash_remaining'),
    ]

    operations = [
        # ─── New auto-calculated fields ───
        migrations.AddField(
            model_name='handoverledger',
            name='projects_created',
            field=models.PositiveIntegerField(
                default=0, verbose_name='Projects Created',
                help_text='Projects created during the tenure period. Auto-calculated.'
            ),
        ),
        migrations.AddField(
            model_name='handoverledger',
            name='pledges_made',
            field=models.PositiveIntegerField(
                default=0, verbose_name='Pledges Made This Tenure',
                help_text='Pledges (money, material, or labour) made during the tenure period. Auto-calculated.'
            ),
        ),
        migrations.AddField(
            model_name='handoverledger',
            name='pledge_total_value',
            field=models.DecimalField(
                decimal_places=2, default=0.0, max_digits=15,
                verbose_name='Total Pledge Value',
                help_text='Total pledged value of Money pledges made during the tenure period. Auto-calculated.'
            ),
        ),
        migrations.AddField(
            model_name='handoverledger',
            name='motorcycle_acquired',
            field=models.PositiveIntegerField(
                default=0, verbose_name='Motorcycles Acquired',
                help_text='Motorcycles acquired during the tenure period. Auto-calculated.'
            ),
        ),

        # ─── Relabelled existing fields (verbose_name/help_text only — no
        # column changes, so no data is affected) ───
        migrations.AlterField(
            model_name='handoverledger',
            name='bank_balance',
            field=models.DecimalField(
                decimal_places=2, default=0.0, max_digits=15,
                verbose_name='Bank Balance (Legacy)',
                help_text='Deprecated — superseded by Physical Cash at Hand. Retained for historical records only.'
            ),
        ),
        migrations.AlterField(
            model_name='handoverledger',
            name='cash_balance',
            field=models.DecimalField(
                decimal_places=2, default=0.0, max_digits=15,
                verbose_name='Cash Balance (Legacy)',
                help_text='Deprecated — superseded by Physical Cash at Hand. Retained for historical records only.'
            ),
        ),
        migrations.AlterField(
            model_name='handoverledger',
            name='cash_remaining',
            field=models.DecimalField(
                decimal_places=2, default=0.0, max_digits=15,
                verbose_name='Physical Cash at Hand',
                help_text='Cash physically counted and held at handover. The only figure on this ledger entered by hand. Administrator-only field.'
            ),
        ),
        migrations.AlterField(
            model_name='handoverledger',
            name='total_income',
            field=models.DecimalField(
                decimal_places=2, default=0.0, max_digits=15,
                verbose_name='Other Income (Contributions)',
                help_text='All non-dues, non-donation, non-case-fine income recorded during the tenure period. Auto-calculated.'
            ),
        ),
        migrations.AlterField(
            model_name='handoverledger',
            name='total_dues',
            field=models.DecimalField(
                decimal_places=2, default=0.0, max_digits=15,
                verbose_name='Yearly Dues Collected',
                help_text='Dues payments recorded during the tenure period. Auto-calculated.'
            ),
        ),
        migrations.AlterField(
            model_name='handoverledger',
            name='total_donations',
            field=models.DecimalField(
                decimal_places=2, default=0.0, max_digits=15,
                verbose_name='Total Project Donations',
                help_text='Confirmed project donations received during the tenure period. Auto-calculated.'
            ),
        ),
        migrations.AlterField(
            model_name='handoverledger',
            name='taskforce_revenue',
            field=models.DecimalField(
                decimal_places=2, default=0.0, max_digits=15,
                verbose_name='Case Fines Revenue',
                help_text='Fines from resolved case files during the tenure period. Auto-calculated.'
            ),
        ),
        migrations.AlterField(
            model_name='handoverledger',
            name='total_expenses',
            field=models.DecimalField(
                decimal_places=2, default=0.0, max_digits=15,
                verbose_name='Total Expenses',
                help_text='Expenses recorded during the tenure period. Auto-calculated.'
            ),
        ),
        migrations.AlterField(
            model_name='handoverledger',
            name='cases_total',
            field=models.PositiveIntegerField(default=0, verbose_name='Cases Handled'),
        ),
        migrations.AlterField(
            model_name='handoverledger',
            name='projects_at_hand',
            field=models.PositiveIntegerField(default=0, verbose_name='Projects In Progress / Handed Over'),
        ),
    ]
