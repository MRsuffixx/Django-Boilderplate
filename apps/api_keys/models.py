from django.conf import settings
from django.db import models
from django.utils import timezone

from common.models import UUIDModel


class APIKey(UUIDModel):
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="api_keys")
    name = models.CharField(max_length=100)
    prefix = models.CharField(max_length=16, unique=True, db_index=True)
    key_hash = models.CharField(max_length=64, editable=False)
    scopes = models.JSONField(default=list)
    created_at = models.DateTimeField(auto_now_add=True)
    last_used_at = models.DateTimeField(null=True, blank=True)
    last_used_ip = models.GenericIPAddressField(null=True, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True, db_index=True)
    revoked_at = models.DateTimeField(null=True, blank=True, db_index=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["owner", "revoked_at", "expires_at"], name="api_key_owner_active_idx")]

    @property
    def is_active(self) -> bool:
        return self.revoked_at is None and (self.expires_at is None or self.expires_at > timezone.now())

    def __str__(self) -> str:
        return f"{self.name} ({self.prefix})"
