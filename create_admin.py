import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oya_system.settings')
django.setup()

from django.contrib.auth import get_user_model

User = get_user_model()

# Change these to what you want your login to be
username = os.environ.get("ADMIN_USERNAME", "admin")
email = os.environ.get("ADMIN_EMAIL", "admin@example.com")
password = os.environ.get("ADMIN_PASSWORD", "YourSecurePassword123")

if not User.objects.filter(username=username).exists():
    print(f"Creating superuser: {username}")
    User.objects.create_superuser(username, email, password)
else:
    print(f"Superuser {username} already exists.")