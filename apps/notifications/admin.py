from django.contrib import admin

from apps.notifications.models import Notification
from common.admin import AuditAdminMixin


@admin.register(Notification)
class NotificationAdmin(AuditAdminMixin, admin.ModelAdmin):
    list_display = ["title", "user", "type", "read_at", "expires_at", "created_at"]
    list_filter = ["type", "read_at", "expires_at", "created_at"]
    search_fields = ["title", "message", "user__email"]
    autocomplete_fields = ["user"]
    readonly_fields = ["id", "created_at"]
