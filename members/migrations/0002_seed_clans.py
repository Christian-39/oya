# members/migrations/0002_seed_clans.py
from django.db import migrations

def seed_clans(apps, schema_editor):
    Clan = apps.get_model("members", "Clan")
    clans = [
        "Umu Onoja",
        "Umu Osede", 
        "Umu Edoga",
        "Umu Nna Ose",
        "Umu Igwurube",
        "Others",
    ]
    for clan_name in clans:
        Clan.objects.get_or_create(name=clan_name)

def remove_clans(apps, schema_editor):
    Clan = apps.get_model("members", "Clan")
    Clan.objects.filter(name__in=[
        "Umu Onoja",
        "Umu Osede",
        "Umu Edoga",
        "Umu Nna Ose",
        "Umu Igwurube",
        "Others",
    ]).delete()

class Migration(migrations.Migration):
    dependencies = [
        ("members", "0001_initial"),  # Adjust to your initial migration
    ]

    operations = [
        migrations.RunPython(seed_clans, remove_clans),
    ]