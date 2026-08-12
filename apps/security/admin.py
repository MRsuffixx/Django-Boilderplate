from django.contrib import admin

from apps.security.models import SecurityEvent


@admin.register(SecurityEvent)
class SecurityEventAdmin(admin.ModelAdmin):
    list_display = ["event_type", "user", "ip_address", "request_id", "created_at"]
    list_filter = ["event_type", "created_at"]
    search_fields = ["user__email", "request_id", "ip_address"]
    readonly_fields = [field.name for field in SecurityEvent._meta.fields]

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
