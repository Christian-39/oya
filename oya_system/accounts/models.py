from django.db import models


class Member(models.Model):
    ROLE_CHOICES = [
        ('admin', 'Admin'),
        ('executive', 'Executive'),
        ('floor', 'Floor Member'),
    ]

    STATUS_CHOICES = [
        ('active', 'Active'),
        ('inactive', 'Inactive'),
        ('suspended', 'Suspended'),
    ]

    serial_number = models.CharField(max_length=20, unique=True)
    full_name = models.CharField(max_length=200)
    phone_number = models.CharField(max_length=20)
    gender = models.CharField(max_length=10)
    age = models.PositiveIntegerField()
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    executive_position = models.CharField(max_length=100, null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES)
    year_joined = models.PositiveIntegerField()
    password = models.CharField(max_length=128)  # hashed later
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.full_name} ({self.executive_position})" if self.executive_position else self.full_name


class Executive(models.Model):
    POSITION_CHOICES = [
        ('President', 'President'),
        ('Deputy President', 'Deputy President'),
        ('Secretary', 'Secretary'),
        ('Assistant Secretary', 'Assistant Secretary'),
        ('Treasurer', 'Treasurer'),
        ('Financial Secretary', 'Financial Secretary'),
        ('Assistant Financial Secretary', 'Assistant Financial Secretary'),
        ('PRO', 'PRO'),
        ('Assistant PRO', 'Assistant PRO'),
        ('DOS', 'DOS'),
        ('Assistant DOS', 'Assistant DOS'),
        ('Provost 1', 'Provost 1'),
        ('Provost 2', 'Provost 2'),
        ('Provost 3', 'Provost 3'),
        ('Auditor 1', 'Auditor 1'),
        ('Auditor 2', 'Auditor 2'),
    ]

    member = models.OneToOneField(Member, on_delete=models.CASCADE)
    position = models.CharField(max_length=100, choices=POSITION_CHOICES)

    def __str__(self):
        return f"{self.member.full_name} - {self.position}"


class ExecutiveTenure(models.Model):
    name = models.CharField(max_length=100)
    start_year = models.PositiveIntegerField()
    end_year = models.PositiveIntegerField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.name} ({self.start_year} - {self.end_year or 'Present'})"
