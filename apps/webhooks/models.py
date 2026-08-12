from __future__ import annotations

from django.conf import settings
from django.db import models

from common.models import TimeStampedModel, UUIDModel


class WebhookEndpoint(UUIDModel, TimeStampedModel):
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="webhook_endpoints",
    )
    name = models.CharField(max_length=100)
    url = models.URLField(max_length=500)
    event_types = models.JSONField(default=list)
    secret_hash = models.CharField(max_length=64, editable=False)
    encrypted_secret = models.TextField(editable=False)
    is_active = models.BooleanField(default=True, db_index=True)

    def __str__(self) -> str:
        return self.name


class WebhookEvent(UUIDModel):
    event_type = models.CharField(max_length=150, db_index=True)
    payload = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)


class DeliveryStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    PROCESSING = "processing", "Processing"
    SUCCEEDED = "succeeded", "Succeeded"
    FAILED = "failed", "Failed"
    ABANDONED = "abandoned", "Abandoned"


class WebhookDelivery(UUIDModel):
    endpoint = models.ForeignKey(
        WebhookEndpoint, on_delete=models.CASCADE, related_name="deliveries"
    )
    event = models.ForeignKey(WebhookEvent, on_delete=models.CASCADE, related_name="deliveries")
    status = models.CharField(
        max_length=16, choices=DeliveryStatus.choices, default=DeliveryStatus.PENDING, db_index=True
    )
    attempt_count = models.PositiveSmallIntegerField(default=0)
    response_code = models.PositiveSmallIntegerField(null=True, blank=True)
    response_body = models.TextField(blank=True)
    last_attempt_at = models.DateTimeField(null=True, blank=True)
    next_retry_at = models.DateTimeField(null=True, blank=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["endpoint", "event"], name="webhook_endpoint_event_unique"
            )
        ]
        indexes = [
            models.Index(fields=["status", "next_retry_at"], name="webhook_pending_retry_idx")
        ]
