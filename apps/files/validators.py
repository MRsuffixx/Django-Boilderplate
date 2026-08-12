from __future__ import annotations

import hashlib
from collections.abc import Callable, Collection
from pathlib import Path

import filetype
from django.conf import settings
from django.core.exceptions import ValidationError
from PIL import Image, UnidentifiedImageError


class SecureFileValidator:
    def __init__(
        self,
        *,
        allowed_extensions: Collection[str],
        allowed_mime_types: Collection[str],
        max_size: int | None = None,
        malware_scanner: Callable | None = None,
    ):
        self.allowed_extensions = {item.lower().lstrip(".") for item in allowed_extensions}
        self.allowed_mime_types = set(allowed_mime_types)
        self.max_size = max_size or settings.MAX_UPLOAD_SIZE
        self.malware_scanner = malware_scanner

    def __call__(self, uploaded_file) -> dict[str, str | int]:
        extension = Path(uploaded_file.name).suffix.lower().lstrip(".")
        if extension not in self.allowed_extensions:
            raise ValidationError("This file extension is not allowed.", code="invalid_extension")
        if uploaded_file.size > self.max_size:
            raise ValidationError("This file is too large.", code="file_too_large")
        sample = uploaded_file.read(min(uploaded_file.size, 262_144))
        uploaded_file.seek(0)
        guessed = filetype.guess(sample)
        detected_mime = guessed.mime if guessed else "application/octet-stream"
        if detected_mime not in self.allowed_mime_types:
            raise ValidationError(
                "The file content type is not allowed.", code="invalid_content_type"
            )
        if detected_mime.startswith("image/"):
            try:
                with Image.open(uploaded_file) as image:
                    width, height = image.size
                    if width * height > settings.MAX_IMAGE_PIXELS:
                        raise ValidationError(
                            "Image dimensions are too large.", code="image_too_large"
                        )
                    image.verify()
            except (Image.DecompressionBombError, UnidentifiedImageError, OSError) as exc:
                raise ValidationError("The image is invalid.", code="invalid_image") from exc
            finally:
                uploaded_file.seek(0)
        if self.malware_scanner:
            self.malware_scanner(uploaded_file)
            uploaded_file.seek(0)
        digest = hashlib.sha256()
        for chunk in uploaded_file.chunks():
            digest.update(chunk)
        uploaded_file.seek(0)
        return {
            "content_type": detected_mime,
            "size": uploaded_file.size,
            "checksum_sha256": digest.hexdigest(),
        }
