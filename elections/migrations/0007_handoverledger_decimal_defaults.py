from decimal import Decimal
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("elections", "0006_election_results_applied_at"),
    ]

    operations = [
        migrations.AlterField(
            model_name="handoverledger",
            name="bank_balance",
            field=models.DecimalField(
                decimal_places=2,
                default=Decimal("0.00"),
                help_text="Deprecated — superseded by Physical Cash at Hand. Retained for historical records only.",
                max_digits=15,
                verbose_name="Bank Balance (Legacy)",
            ),
        ),
        migrations.AlterField(
            model_name="handoverledger",
            name="cash_balance",
            field=models.DecimalField(
                decimal_places=2,
                default=Decimal("0.00"),
                help_text="Deprecated — superseded by Physical Cash at Hand. Retained for historical records only.",
                max_digits=15,
                verbose_name="Cash Balance (Legacy)",
            ),
        ),
        migrations.AlterField(
            model_name="handoverledger",
            name="total_income",
            field=models.DecimalField(
                decimal_places=2,
                default=Decimal("0.00"),
                help_text="All non-dues, non-donation, non-case-fine income recorded during the tenure period. Auto-calculated.",
                max_digits=15,
                verbose_name="Other Income (Contributions)",
            ),
        ),
        migrations.AlterField(
            model_name="handoverledger",
            name="total_dues",
            field=models.DecimalField(
                decimal_places=2,
                default=Decimal("0.00"),
                help_text="Dues payments recorded during the tenure period. Auto-calculated.",
                max_digits=15,
                verbose_name="Yearly Dues Collected",
            ),
        ),
        migrations.AlterField(
            model_name="handoverledger",
            name="total_donations",
            field=models.DecimalField(
                decimal_places=2,
                default=Decimal("0.00"),
                help_text="Confirmed project donations received during the tenure period. Auto-calculated.",
                max_digits=15,
                verbose_name="Total Project Donations",
            ),
        ),
        migrations.AlterField(
            model_name="handoverledger",
            name="taskforce_revenue",
            field=models.DecimalField(
                decimal_places=2,
                default=Decimal("0.00"),
                help_text="Fines from resolved case files during the tenure period. Auto-calculated.",
                max_digits=15,
                verbose_name="Case Fines Revenue",
            ),
        ),
        migrations.AlterField(
            model_name="handoverledger",
            name="total_expenses",
            field=models.DecimalField(
                decimal_places=2,
                default=Decimal("0.00"),
                help_text="Expenses recorded during the tenure period. Auto-calculated.",
                max_digits=15,
                verbose_name="Total Expenses",
            ),
        ),
        migrations.AlterField(
            model_name="handoverledger",
            name="pledge_total_value",
            field=models.DecimalField(
                decimal_places=2,
                default=Decimal("0.00"),
                help_text="Total pledged value of Money pledges made during the tenure period. Auto-calculated.",
                max_digits=15,
                verbose_name="Total Pledge Value",
            ),
        ),
    ]
