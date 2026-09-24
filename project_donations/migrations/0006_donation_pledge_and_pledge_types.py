# Generated manually (no network access to run makemigrations in this
# environment) — follows the same style Django would produce for this
# model change. Verify with `python manage.py makemigrations --check`
# before applying in your environment.

import django.db.models.deletion
from decimal import Decimal
from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('project_donations', '0005_rename_proj_don_donationtype_idx_project_don_donatio_d438a6_idx_and_more'),
        ('members', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        # ─── Donation: "Pending" → "Pledge" ───
        migrations.AlterField(
            model_name='donation',
            name='status',
            field=models.CharField(
                choices=[('PLEDGE', 'Pledge'), ('CONFIRMED', 'Confirmed'), ('CANCELLED', 'Cancelled')],
                default='CONFIRMED', max_length=20, verbose_name='Status',
                help_text='Pledge: donor has committed but not yet fulfilled — auto-creates a linked Pledge record. Confirmed: contribution received.'
            ),
        ),

        # ─── Pledge: support every donor/contribution type, same as Donation ───
        migrations.AlterField(
            model_name='pledge',
            name='member',
            field=models.ForeignKey(
                blank=True, null=True, on_delete=django.db.models.deletion.PROTECT,
                related_name='pledges', to='members.member', verbose_name='Member'
            ),
        ),
        migrations.AlterField(
            model_name='pledge',
            name='pledged_amount',
            field=models.DecimalField(
                blank=True, decimal_places=2, max_digits=15, null=True,
                validators=[MinValueValidator(Decimal('0.01'))],
                help_text='Required for Money pledges.', verbose_name='Pledged Amount'
            ),
        ),
        migrations.AddField(
            model_name='pledge',
            name='donor_type',
            field=models.CharField(
                choices=[('MEMBER', 'OYA Member'), ('OUTSIDE', 'Outside Donor')],
                default='MEMBER', max_length=10, verbose_name='Donor Type'
            ),
        ),
        migrations.AddField(
            model_name='pledge',
            name='donation_type',
            field=models.CharField(
                choices=[('MONEY', 'Money'), ('MATERIAL', 'Material'), ('LABOUR', 'Labour')],
                db_index=True, default='MONEY', max_length=10, verbose_name='Contribution Type'
            ),
        ),
        migrations.AddField(
            model_name='pledge',
            name='outside_donor',
            field=models.ForeignKey(
                blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL,
                related_name='pledges', to='project_donations.outsidedonor', verbose_name='Outside Donor'
            ),
        ),
        migrations.AddField(
            model_name='pledge',
            name='material_name',
            field=models.CharField(blank=True, max_length=255, verbose_name='Material Name'),
        ),
        migrations.AddField(
            model_name='pledge',
            name='quantity',
            field=models.CharField(blank=True, max_length=100, verbose_name='Quantity'),
        ),
        migrations.AddField(
            model_name='pledge',
            name='labour_type',
            field=models.CharField(blank=True, max_length=255, verbose_name='Labour Type'),
        ),
        migrations.AddField(
            model_name='pledge',
            name='number_of_days',
            field=models.PositiveIntegerField(blank=True, null=True, verbose_name='Number of Days'),
        ),
        migrations.AddField(
            model_name='pledge',
            name='estimated_value',
            field=models.DecimalField(
                blank=True, decimal_places=2, max_digits=15, null=True,
                validators=[MinValueValidator(Decimal('0.00'))],
                help_text='Optional. Informational only for Material/Labour pledges.',
                verbose_name='Estimated Value'
            ),
        ),
        migrations.AddIndex(
            model_name='pledge',
            index=models.Index(fields=['outside_donor'], name='project_don_outside_ac1234_idx'),
        ),
        migrations.AddIndex(
            model_name='pledge',
            index=models.Index(fields=['donation_type'], name='project_don_donatio_ab5678_idx'),
        ),

        # ─── Donation ↔ Pledge link ───
        migrations.AddField(
            model_name='donation',
            name='pledge',
            field=models.OneToOneField(
                blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL,
                related_name='source_donation', to='project_donations.pledge',
                verbose_name='Linked Pledge Record',
                help_text="Auto-managed. Set when this donation's status is Pledge; keeps the Pledges module in sync."
            ),
        ),
    ]
