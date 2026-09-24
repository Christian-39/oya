"""
Core models and utilities for OYA.
"""
from django.db import models
import uuid


class BaseModel(models.Model):
    """Abstract base model with common fields."""
    id = models.BigAutoField(primary_key=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True
        ordering = ["-created_at"]


class TimestampMixin:
    """Mixin for timestamp fields."""
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
