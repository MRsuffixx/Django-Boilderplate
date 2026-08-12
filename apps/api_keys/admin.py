from django.contrib import admin

from apps.api_keys.models import APIKey
from apps.api_keys.services import APIKeyService
from common.admin import AuditAdminMixin


@admin.register(APIKey)
class APIKeyAdmin(AuditAdminMixin, admin.ModelAdmin):
    list_display = [
        "name",
        "owner",
        "prefix",
        "created_at",
        "last_used_at",
        "expires_at",
        "revoked_at",
    ]
    list_filter = ["created_at", "last_used_at", "expires_at", "revoked_at"]
    search_fields = ["name", "owner__email", "prefix"]
    autocomplete_fields = ["owner"]
    readonly_fields = ["id", "prefix", "created_at", "last_used_at", "last_used_ip", "revoked_at"]
    exclude = ["key_hash"]
    actions = ["revoke_selected"]

    @admin.action(description="Revoke selected API keys")
    def revoke_selected(self, request, queryset):
        for api_key in queryset.filter(revoked_at__isnull=True):
            APIKeyService.revoke(api_key=api_key, actor=request.user, request=request)
