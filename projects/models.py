from django.db import models
from accounts.models import ExecutiveTenure, Member


class Project(models.Model):
    STATUS_CHOICES = [
        ('ongoing', 'Ongoing'),
        ('completed', 'Completed'),
        ('future', 'Future'),
        ('handed_over', 'Handed Over'),
    ]

    title = models.CharField(max_length=200)
    description = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES)
    started_by_tenure = models.ForeignKey(
        ExecutiveTenure, on_delete=models.SET_NULL, null=True, related_name='projects_started'
    )
    completed_by_tenure = models.ForeignKey(
        ExecutiveTenure, on_delete=models.SET_NULL, null=True, blank=True, related_name='projects_completed'
    )
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    created_by = models.ForeignKey(Member, on_delete=models.SET_NULL, null=True)

    def __str__(self):
        return self.title
