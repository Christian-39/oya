from django.apps import AppConfig


class ProjectDonationsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "project_donations"
    verbose_name = "Project Donations"

    def ready(self):
        import project_donations.signals