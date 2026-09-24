# Generated manually (no network access to run makemigrations in this
# environment) — follows the same style Django would produce for this
# model change. Verify with `python manage.py makemigrations --check`
# before applying in your environment.

import django.db.models.deletion
import django.utils.timezone
from decimal import Decimal
from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('project_donations', '0003_donation_income'),
        ('projects', '0003_project_include_in_group_reports'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        # ─── Feature 5: Donation types (Money / Material / Labour) ───
        migrations.AlterField(
            model_name='donation',
            name='amount',
            field=models.DecimalField(
                blank=True, decimal_places=2, max_digits=15, null=True,
                validators=[MinValueValidator(Decimal('0.00'))],
                help_text='Required for Money donations.', verbose_name='Amount'
            ),
        ),
        migrations.AddField(
            model_name='donation',
            name='donation_type',
            field=models.CharField(
                choices=[('MONEY', 'Money'), ('MATERIAL', 'Material'), ('LABOUR', 'Labour')],
                db_index=True, default='MONEY', max_length=10, verbose_name='Donation Type'
            ),
        ),
        migrations.AddField(
            model_name='donation',
            name='receipt',
            field=models.FileField(blank=True, null=True, upload_to='donations/receipts/%Y/%m/', verbose_name='Receipt'),
        ),
        migrations.AddField(
            model_name='donation',
            name='material_name',
            field=models.CharField(blank=True, max_length=255, verbose_name='Material Name'),
        ),
        migrations.AddField(
            model_name='donation',
            name='quantity',
            field=models.CharField(blank=True, max_length=100, verbose_name='Quantity'),
        ),
        migrations.AddField(
            model_name='donation',
            name='labour_type',
            field=models.CharField(blank=True, max_length=255, verbose_name='Labour Type'),
        ),
        migrations.AddField(
            model_name='donation',
            name='number_of_days',
            field=models.PositiveIntegerField(blank=True, null=True, verbose_name='Number of Days'),
        ),
        migrations.AddField(
            model_name='donation',
            name='estimated_value',
            field=models.DecimalField(
                blank=True, decimal_places=2, max_digits=15, null=True,
                validators=[MinValueValidator(Decimal('0.00'))],
                help_text='Optional. Informational only unless treasury recording is enabled for Material.',
                verbose_name='Estimated Value'
            ),
        ),
        migrations.AddField(
            model_name='donation',
            name='remarks',
            field=models.TextField(blank=True, verbose_name='Remarks'),
        ),
        migrations.AddField(
            model_name='donation',
            name='update_treasury',
            field=models.BooleanField(
                default=False,
                help_text='Material donations only: if enabled, the estimated value is recorded as income.',
                verbose_name='Update Treasury?'
            ),
        ),
        migrations.AddIndex(
            model_name='donation',
            index=models.Index(fields=['donation_type'], name='proj_don_donationtype_idx'),
        ),

        # ─── Features 6, 7: Pledge / PledgePayment ───
        migrations.CreateModel(
            name='Pledge',
            fields=[
                ('id', models.BigAutoField(primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('pledged_amount', models.DecimalField(
                    decimal_places=2, max_digits=15,
                    validators=[MinValueValidator(Decimal('0.01'))], verbose_name='Pledged Amount'
                )),
                ('due_date', models.DateField(blank=True, null=True, verbose_name='Due Date')),
                ('notes', models.TextField(blank=True, verbose_name='Notes')),
                ('status', models.CharField(
                    choices=[('PENDING', 'Pending'), ('PARTIALLY_PAID', 'Partially Paid'),
                             ('COMPLETED', 'Completed'), ('CANCELLED', 'Cancelled')],
                    db_index=True, default='PENDING', max_length=20, verbose_name='Status'
                )),
                ('created_by', models.ForeignKey(
                    blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL,
                    related_name='pledges_recorded', to=settings.AUTH_USER_MODEL, verbose_name='Recorded By'
                )),
                ('member', models.ForeignKey(
                    on_delete=django.db.models.deletion.PROTECT, related_name='pledges',
                    to='members.member', verbose_name='Member'
                )),
                ('project', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE, related_name='pledges',
                    to='projects.project', verbose_name='Project'
                )),
            ],
            options={
                'verbose_name': 'Pledge',
                'verbose_name_plural': 'Pledges',
                'db_table': 'project_donations_pledge',
                'ordering': ['-created_at'],
            },
        ),
        migrations.AddIndex(
            model_name='pledge',
            index=models.Index(fields=['member'], name='proj_don_pledge_member_idx'),
        ),
        migrations.AddIndex(
            model_name='pledge',
            index=models.Index(fields=['project'], name='proj_don_pledge_project_idx'),
        ),
        migrations.AddIndex(
            model_name='pledge',
            index=models.Index(fields=['status'], name='proj_don_pledge_status_idx'),
        ),
        migrations.AddIndex(
            model_name='pledge',
            index=models.Index(fields=['due_date'], name='proj_don_pledge_duedate_idx'),
        ),
        migrations.CreateModel(
            name='PledgePayment',
            fields=[
                ('id', models.BigAutoField(primary_key=True, serialize=False)),
                ('amount', models.DecimalField(
                    decimal_places=2, max_digits=15,
                    validators=[MinValueValidator(Decimal('0.01'))], verbose_name='Payment Amount'
                )),
                ('payment_date', models.DateField(default=django.utils.timezone.now, verbose_name='Payment Date')),
                ('payment_method', models.CharField(
                    choices=[('CASH', 'Cash'), ('BANK_TRANSFER', 'Bank Transfer'),
                             ('MOBILE_MONEY', 'Mobile Money'), ('CHECK', 'Check'), ('OTHER', 'Other')],
                    default='CASH', max_length=20, verbose_name='Payment Method'
                )),
                ('reference_number', models.CharField(blank=True, max_length=255, verbose_name='Reference Number')),
                ('notes', models.TextField(blank=True, verbose_name='Notes')),
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True)),
                ('donation', models.OneToOneField(
                    blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL,
                    related_name='source_pledge_payment', to='project_donations.donation',
                    verbose_name='Linked Donation Record'
                )),
                ('pledge', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE, related_name='payments',
                    to='project_donations.pledge', verbose_name='Pledge'
                )),
                ('recorded_by', models.ForeignKey(
                    blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL,
                    related_name='pledge_payments_recorded', to=settings.AUTH_USER_MODEL,
                    verbose_name='Recorded By'
                )),
            ],
            options={
                'verbose_name': 'Pledge Payment',
                'verbose_name_plural': 'Pledge Payments',
                'db_table': 'project_donations_pledge_payment',
                'ordering': ['-payment_date', '-created_at'],
            },
        ),
        migrations.AddIndex(
            model_name='pledgepayment',
            index=models.Index(fields=['pledge'], name='proj_don_pp_pledge_idx'),
        ),
        migrations.AddIndex(
            model_name='pledgepayment',
            index=models.Index(fields=['payment_date'], name='proj_don_pp_paydate_idx'),
        ),
    ]
