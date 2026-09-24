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
        ('settingsapp', '0002_systemsettings_favicon_systemsettings_logo'),
        ('members', '0004_member_year_joined_and_more'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='DonationGroup',
            fields=[
                ('id', models.BigAutoField(primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('name', models.CharField(
                    help_text='e.g. G50, Diamond Members, Platinum Donors, Gold Circle',
                    max_length=150, unique=True, verbose_name='Group Name'
                )),
                ('description', models.TextField(blank=True, verbose_name='Description')),
                ('minimum_amount', models.DecimalField(
                    decimal_places=2, default=Decimal('0.00'), max_digits=15,
                    validators=[MinValueValidator(Decimal('0.00'))],
                    verbose_name='Minimum Donation Amount'
                )),
                ('maximum_amount', models.DecimalField(
                    blank=True, decimal_places=2, max_digits=15, null=True,
                    validators=[MinValueValidator(Decimal('0.00'))],
                    help_text='Leave blank for unlimited.',
                    verbose_name='Maximum Donation Amount'
                )),
                ('is_active', models.BooleanField(db_index=True, default=True, verbose_name='Active')),
                ('created_by', models.ForeignKey(
                    blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL,
                    related_name='donation_groups_created', to=settings.AUTH_USER_MODEL,
                    verbose_name='Created By'
                )),
            ],
            options={
                'verbose_name': 'Donation Group',
                'verbose_name_plural': 'Donation Groups',
                'db_table': 'settingsapp_donation_group',
                'ordering': ['name'],
            },
        ),
        migrations.AddIndex(
            model_name='donationgroup',
            index=models.Index(fields=['is_active'], name='settingsapp_dg_active_idx'),
        ),
        migrations.AddIndex(
            model_name='donationgroup',
            index=models.Index(fields=['name'], name='settingsapp_dg_name_idx'),
        ),
        migrations.CreateModel(
            name='DonationGroupMembership',
            fields=[
                ('id', models.BigAutoField(primary_key=True, serialize=False)),
                ('date_added', models.DateField(default=django.utils.timezone.now, verbose_name='Date Added')),
                ('added_by', models.ForeignKey(
                    blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL,
                    related_name='donation_group_assignments_made', to=settings.AUTH_USER_MODEL,
                    verbose_name='Added By'
                )),
                ('group', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE, related_name='memberships',
                    to='settingsapp.donationgroup', verbose_name='Donation Group'
                )),
                ('member', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE, related_name='donation_group_memberships',
                    to='members.member', verbose_name='Member'
                )),
            ],
            options={
                'verbose_name': 'Donation Group Membership',
                'verbose_name_plural': 'Donation Group Memberships',
                'db_table': 'settingsapp_donation_group_membership',
                'ordering': ['-date_added'],
            },
        ),
        migrations.AddIndex(
            model_name='donationgroupmembership',
            index=models.Index(fields=['group', 'member'], name='settingsapp_dgm_grp_mem_idx'),
        ),
        migrations.AddIndex(
            model_name='donationgroupmembership',
            index=models.Index(fields=['member'], name='settingsapp_dgm_member_idx'),
        ),
        migrations.AlterUniqueTogether(
            name='donationgroupmembership',
            unique_together={('group', 'member')},
        ),
    ]
