from django.contrib import admin
from .models import Member
import hashlib


@admin.register(Member)
class MemberAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'serial_number', 'role')

    def save_model(self, request, obj, form, change):
        if len(obj.password) == 6:
            obj.password = hashlib.sha256(obj.password.encode()).hexdigest()
        super().save_model(request, obj, form, change)


