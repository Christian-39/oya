from django.db import models
from accounts.models import Member


class TaskForce(models.Model):
    member = models.ForeignKey(Member, on_delete=models.CASCADE)
    role_in_taskforce = models.CharField(max_length=100)
    phone_number = models.CharField(max_length=20)
    status = models.CharField(max_length=50)

    def __str__(self):
        return self.member.full_name


class Motorcycle(models.Model):
    bike_number = models.CharField(max_length=50)
    plate_number = models.CharField(max_length=50)
    condition = models.CharField(max_length=100)
    assigned_to = models.ForeignKey(TaskForce, on_delete=models.SET_NULL, null=True, blank=True)
    status = models.CharField(max_length=50)

    def __str__(self):
        return self.bike_number
