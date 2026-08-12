from django.contrib import admin

from apps.notifications.models import Notification


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ["title", "user", "type", "read_at", "expires_at", "created_at"]
    list_filter = ["type", "read_at", "expires_at", "created_at"]
    search_fields = ["title", "message", "user__email"]
    autocomplete_fields = ["user"]
    readonly_fields = ["id", "created_at"]
