from django.contrib.auth.models import User
from django.db import models


class Case(models.Model):
    STATUS_CHOICES = [('pending', 'Pending'), ('resolved', 'Resolved'), ('escalated', 'Escalated')]
    HANDLED_BY = [('taskforce', 'Task Force'), ('executives', 'Executives')]

    title = models.CharField(max_length=200)
    description = models.TextField()
    presented_by = models.ForeignKey(User, on_delete=models.CASCADE)
    date_presented = models.DateField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES)
    handled_by = models.CharField(max_length=20, choices=HANDLED_BY)

    def __str__(self):
        return self.title
