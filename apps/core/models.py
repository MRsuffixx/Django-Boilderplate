from __future__ import annotations

import re

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

from common.models import TimeStampedModel, UUIDModel


class SettingValueType(models.TextChoices):
    STRING = "string", "String"
    INTEGER = "integer", "Integer"
    BOOLEAN = "boolean", "Boolean"
    JSON = "json", "JSON"


class Setting(UUIDModel, TimeStampedModel):
    key = models.CharField(max_length=150, unique=True)
    value = models.JSONField()
    value_type = models.CharField(
        max_length=16, choices=SettingValueType.choices, default=SettingValueType.STRING
    )
    group = models.CharField(max_length=64, default="general", db_index=True)
    is_public = models.BooleanField(default=False)
    description = models.TextField(blank=True)

    def clean(self):
        if re.search(
            r"(^|[._-])(password|secret|credential|private_key|access_key|token|dsn)($|[._-])",
            self.key,
            re.IGNORECASE,
        ):
            raise ValidationError(
                {"key": "Secret-like values must be stored outside the database."}
            )
        valid = {
            SettingValueType.STRING: lambda value: isinstance(value, str),
            SettingValueType.INTEGER: lambda value: (
                isinstance(value, int) and not isinstance(value, bool)
            ),
            SettingValueType.BOOLEAN: lambda value: isinstance(value, bool),
            SettingValueType.JSON: lambda _value: True,
        }
        if not valid[self.value_type](self.value):
            raise ValidationError({"value": f"Value does not match type {self.value_type}."})

    def __str__(self) -> str:
        return self.key


class FeatureFlag(UUIDModel, TimeStampedModel):
    key = models.CharField(max_length=150, unique=True)
    enabled = models.BooleanField(default=False, db_index=True)
    description = models.TextField(blank=True)

    def __str__(self) -> str:
        return self.key


class IdempotencyRecord(UUIDModel):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="idempotency_records",
    )
    key_hash = models.CharField(max_length=64)
    request_method = models.CharField(max_length=8)
    request_path = models.CharField(max_length=500)
    request_hash = models.CharField(max_length=64)
    response_status = models.PositiveSmallIntegerField(null=True, blank=True)
    response_body = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(db_index=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user", "key_hash"], name="core_idempotency_user_key_unique"
            )
        ]
        indexes = [models.Index(fields=["expires_at"], name="core_idempotency_expiry_idx")]
