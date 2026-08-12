from django.contrib import admin

from apps.authentication.models import OneTimeToken, RecoveryCode, TwoFactorCredential, UserSession


@admin.register(UserSession)
class UserSessionAdmin(admin.ModelAdmin):
    list_display = ["identifier", "user", "ip_address", "browser", "operating_system", "device", "last_activity_at", "revoked_at"]
    list_filter = ["device", "revoked_at", "created_at", "last_activity_at"]
    search_fields = ["identifier", "user__email", "ip_address", "browser", "operating_system"]
    autocomplete_fields = ["user"]
    readonly_fields = [
        "id",
        "identifier",
        "user",
        "ip_address",
        "user_agent",
        "browser",
        "operating_system",
        "device",
        "location",
        "created_at",
        "last_activity_at",
        "revoked_at",
    ]
    exclude = ["session_key_hash", "encrypted_session_key"]

    def has_add_permission(self, request):
        return False


@admin.register(OneTimeToken)
class OneTimeTokenAdmin(admin.ModelAdmin):
    list_display = ["user", "purpose", "created_at", "expires_at", "used_at"]
    list_filter = ["purpose", "created_at", "expires_at", "used_at"]
    search_fields = ["user__email"]
    readonly_fields = ["id", "user", "purpose", "metadata", "created_at", "expires_at", "used_at"]
    exclude = ["token_hash"]

    def has_add_permission(self, request):
        return False


@admin.register(TwoFactorCredential)
class TwoFactorCredentialAdmin(admin.ModelAdmin):
    list_display = ["user", "created_at", "confirmed_at", "disabled_at"]
    list_filter = ["confirmed_at", "disabled_at"]
    search_fields = ["user__email"]
    readonly_fields = ["id", "user", "created_at", "confirmed_at", "disabled_at"]
    exclude = ["encrypted_secret"]

    def has_add_permission(self, request):
        return False


@admin.register(RecoveryCode)
class RecoveryCodeAdmin(admin.ModelAdmin):
    list_display = ["credential", "created_at", "used_at"]
    list_filter = ["created_at", "used_at"]
    readonly_fields = ["id", "credential", "created_at", "used_at"]
    exclude = ["code_hash"]

    def has_add_permission(self, request):
        return False
