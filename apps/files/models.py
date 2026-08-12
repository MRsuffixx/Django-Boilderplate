from __future__ import annotations

import uuid

from django.conf import settings
from django.db import models

from common.models import UUIDModel


def secure_upload_path(instance: StoredFile, filename: str) -> str:
    extension = filename.rsplit(".", 1)[-1].lower() if "." in filename else "bin"
    owner = str(instance.owner_id or "system")
    return f"uploads/{owner}/{uuid.uuid4().hex}.{extension}"


class FileStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    READY = "ready", "Ready"
    QUARANTINED = "quarantined", "Quarantined"
    REJECTED = "rejected", "Rejected"


class StoredFile(UUIDModel):
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="stored_files",
    )
    file = models.FileField(upload_to=secure_upload_path, max_length=500)
    original_name = models.CharField(max_length=255)
    content_type = models.CharField(max_length=150)
    size = models.PositiveBigIntegerField()
    checksum_sha256 = models.CharField(max_length=64, db_index=True)
    status = models.CharField(
        max_length=16, choices=FileStatus.choices, default=FileStatus.PENDING, db_index=True
    )
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    last_accessed_at = models.DateTimeField(null=True, blank=True)
    deleted_at = models.DateTimeField(null=True, blank=True, db_index=True)

    class Meta:
        indexes = [
            models.Index(fields=["owner", "status", "created_at"], name="file_owner_status_idx")
        ]
