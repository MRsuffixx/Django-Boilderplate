from django.conf import settings
from django.db import models

from common.models import UUIDModel


class SecurityEventType(models.TextChoices):
    LOGIN_SUCCESS = "login_success", "Login successful"
    LOGIN_FAILED = "login_failed", "Login failed"
    NEW_DEVICE_LOGIN = "new_device_login", "New device login"
    PASSWORD_CHANGED = "password_changed", "Password changed"
    PASSWORD_RESET = "password_reset", "Password reset"
    EMAIL_CHANGED = "email_changed", "Email changed"
    TWO_FACTOR_ENABLED = "two_factor_enabled", "Two-factor authentication enabled"
    TWO_FACTOR_DISABLED = "two_factor_disabled", "Two-factor authentication disabled"
    RECOVERY_CODE_USED = "recovery_code_used", "Recovery code used"
    SESSION_REVOKED = "session_revoked", "Session revoked"
    ACCOUNT_LOCKED = "account_locked", "Account locked"
    ACCOUNT_UNLOCKED = "account_unlocked", "Account unlocked"
    ACCOUNT_DEACTIVATED = "account_deactivated", "Account deactivated"
    ACCOUNT_DELETED = "account_deleted", "Account deleted"
    API_KEY_CREATED = "api_key_created", "API key created"
    API_KEY_REVOKED = "api_key_revoked", "API key revoked"


class SecurityEvent(UUIDModel):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="security_events",
    )
    event_type = models.CharField(max_length=40, choices=SecurityEventType.choices, db_index=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    request_id = models.CharField(max_length=64, blank=True, db_index=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["user", "created_at"], name="security_event_user_time_idx")]
