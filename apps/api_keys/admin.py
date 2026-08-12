from django.contrib import admin
from django.utils import timezone

from apps.api_keys.models import APIKey


@admin.register(APIKey)
class APIKeyAdmin(admin.ModelAdmin):
    list_display = ["name", "owner", "prefix", "created_at", "last_used_at", "expires_at", "revoked_at"]
    list_filter = ["created_at", "last_used_at", "expires_at", "revoked_at"]
    search_fields = ["name", "owner__email", "prefix"]
    autocomplete_fields = ["owner"]
    readonly_fields = ["id", "prefix", "created_at", "last_used_at", "last_used_ip", "revoked_at"]
    exclude = ["key_hash"]
    actions = ["revoke_selected"]

    @admin.action(description="Revoke selected API keys")
    def revoke_selected(self, request, queryset):
        queryset.filter(revoked_at__isnull=True).update(revoked_at=timezone.now())
