from __future__ import annotations

from django.db import transaction

from apps.files.models import FileStatus, StoredFile
from apps.files.validators import SecureFileValidator


class FileService:
    @staticmethod
    @transaction.atomic
    def store(*, owner, uploaded_file, validator: SecureFileValidator) -> StoredFile:
        metadata = validator(uploaded_file)
        return StoredFile.objects.create(
            owner=owner,
            file=uploaded_file,
            original_name=uploaded_file.name[:255],
            content_type=metadata["content_type"],
            size=metadata["size"],
            checksum_sha256=metadata["checksum_sha256"],
            status=FileStatus.READY,
        )
