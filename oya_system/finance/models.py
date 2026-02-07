from django.db import models
from accounts.models import Member
from projects.models import Project


class Contribution(models.Model):
    member = models.ForeignKey(Member, on_delete=models.CASCADE)
    year = models.PositiveIntegerField()
    amount_paid = models.DecimalField(max_digits=10, decimal_places=2)
    payment_date = models.DateField()
    recorded_by = models.ForeignKey(Member, on_delete=models.SET_NULL, null=True, related_name='contributions_recorded')

    class Meta:
        unique_together = ('member', 'year')  # ✅ Prevent duplicate dues per year

    def __str__(self):
        return f"{self.member.full_name} - {self.year} - ₦{self.amount_paid}"


class Income(models.Model):
    date = models.DateField(auto_now_add=True)
    title = models.CharField(max_length=200)
    sender_name = models.CharField(max_length=200)
    sender_id = models.CharField(max_length=50)

    member = models.ForeignKey(
        Member,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='received_incomes'  # 👈 FIX
    )

    amount = models.DecimalField(max_digits=12, decimal_places=2)

    recorded_by = models.ForeignKey(
        Member,
        on_delete=models.SET_NULL,
        null=True,
        related_name='incomes_recorded'  # 👈 FIX
    )

    def __str__(self):
        return f"{self.title} - ₦{self.amount}"


class Finance(models.Model):
    TYPE_CHOICES = [('expense', 'Expense')]

    type = models.CharField(max_length=10, choices=TYPE_CHOICES, default='expense')
    title = models.CharField(max_length=200)
    description = models.TextField()
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    date = models.DateField()
    recorded_by = models.ForeignKey(Member, on_delete=models.SET_NULL, null=True)
    project = models.ForeignKey(Project, on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return f"{self.title} - ₦{self.amount}"
