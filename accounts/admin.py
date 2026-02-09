from django.contrib import admin
from .models import Member, Announcement, MeetingMinute
import hashlib


@admin.register(Member)
class MemberAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'serial_number', 'role')

    def save_model(self, request, obj, form, change):
        if len(obj.password) == 6:
            obj.password = hashlib.sha256(obj.password.encode()).hexdigest()
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