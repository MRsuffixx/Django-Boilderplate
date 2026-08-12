from __future__ import annotations

from django.conf import settings
from django.db import models
from django.utils import timezone

from common.models import UUIDModel


class TokenPurpose(models.TextChoices):
    EMAIL_VERIFICATION = "email_verification", "Email verification"
    PASSWORD_RESET = "password_reset", "Password reset"
    EMAIL_CHANGE = "email_change", "Email change"
    ACCOUNT_DELETION = "account_deletion", "Account deletion"


class OneTimeToken(UUIDModel):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="one_time_tokens")
    purpose = models.CharField(max_length=32, choices=TokenPurpose.choices)
    token_hash = models.CharField(max_length=64, unique=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(db_index=True)
    used_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        indexes = [models.Index(fields=["user", "purpose", "used_at"], name="auth_token_user_purpose_idx")]

    @property
    def is_usable(self) -> bool:
        return self.used_at is None and self.expires_at > timezone.now()


class UserSession(UUIDModel):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="user_sessions")
    identifier = models.CharField(max_length=32, unique=True, editable=False)
    session_key_hash = models.CharField(max_length=64, unique=True, editable=False)
    encrypted_session_key = models.TextField(editable=False)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    browser = models.CharField(max_length=100, blank=True)
    operating_system = models.CharField(max_length=100, blank=True)
    device = models.CharField(max_length=100, blank=True)
    location = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    last_activity_at = models.DateTimeField(auto_now=True, db_index=True)
    revoked_at = models.DateTimeField(null=True, blank=True, db_index=True)

    class Meta:
        ordering = ["-last_activity_at"]
        indexes = [models.Index(fields=["user", "revoked_at", "last_activity_at"], name="auth_session_active_idx")]

    @property
    def is_revoked(self) -> bool:
        return self.revoked_at is not None


class TwoFactorCredential(UUIDModel):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="two_factor")
    encrypted_secret = models.TextField(editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    confirmed_at = models.DateTimeField(null=True, blank=True)
    disabled_at = models.DateTimeField(null=True, blank=True)

    @property
    def is_enabled(self) -> bool:
        return self.confirmed_at is not None and self.disabled_at is None


class RecoveryCode(UUIDModel):
    credential = models.ForeignKey(TwoFactorCredential, on_delete=models.CASCADE, related_name="recovery_codes")
    code_hash = models.CharField(max_length=64, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    used_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["credential", "code_hash"], name="auth_recovery_code_unique")]
