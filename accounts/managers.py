from django.contrib.auth.models import BaseUserManager
from django.utils import timezone

class UserManager(BaseUserManager):
    """Custom user manager for serial number-based authentication."""

    def create_user(self, serial_number, full_name, pin=None, **extra_fields):
        """Create and save a User with the given serial number and PIN."""
        if not serial_number:
            raise ValueError("The Serial Number must be set")
        
        # Pull pin and full_name from extra_fields if Django passes them as kwargs
        if pin is None:
            pin = extra_fields.pop('pin', None)
        if not full_name:
            full_name = extra_fields.pop('full_name', None)

        if not full_name:
            raise ValueError("The Full Name must be set")
        if not pin:
            raise ValueError("The PIN must be set")

        # Set admin defaults if not explicitly provided
        extra_fields.setdefault("role", "ADMIN")
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)

        user = self.model(
            serial_number=serial_number,
            full_name=full_name,
            **extra_fields
        )
        # Use your custom model's hashing function instead of set_password
        user.set_pin(pin) 
        user.save(using=self._db)
        return user

    def create_superuser(self, serial_number, full_name=None, pin=None, **extra_fields):
        """Create and save a SuperUser with the given serial number and PIN."""
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)
        extra_fields.setdefault("role", "ADMIN")

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")

        # Pass variables cleanly down to create_user
        return self.create_user(serial_number, full_name, pin, **extra_fields)
