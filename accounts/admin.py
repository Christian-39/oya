from django.contrib import admin
from django.contrib.auth.hashers import make_password

from .models import Member, Announcement, MeetingMinute
import hashlib

@admin.register(Member)
class MemberAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'serial_number', 'role', 'status')

    def save_model(self, request, obj, form, change):
        if not obj.password.startswith('pbkdf2_sha256$'):
            obj.password = make_password(obj.password)
        super().save_model(request, obj, form, change)


@admin.register(Announcement)
class AnnouncementAdmin(admin.ModelAdmin):
    list_display = ('title', 'created_by', 'created_at', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('title', 'message')


@admin.register(MeetingMinute)
class MeetingMinuteAdmin(admin.ModelAdmin):
    list_display = ('title', 'meeting_date', 'created_by', 'created_at')
    search_fields = ('title', 'content')