import io

import pytest
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image

from apps.files.validators import SecureFileValidator


def _png_file() -> SimpleUploadedFile:
    content = io.BytesIO()
    Image.new("RGB", (10, 10), color="red").save(content, format="PNG")
    return SimpleUploadedFile("picture.png", content.getvalue(), content_type="image/png")


def test_secure_file_validator_uses_content_signature():
    metadata = SecureFileValidator(
        allowed_extensions={"png"},
        allowed_mime_types={"image/png"},
    )(_png_file())

    assert metadata["content_type"] == "image/png"
    assert len(metadata["checksum_sha256"]) == 64


def test_spoofed_extension_is_rejected():
    fake = SimpleUploadedFile("picture.png", b"not really a png", content_type="image/png")

    with pytest.raises(ValidationError):
        SecureFileValidator(
            allowed_extensions={"png"},
            allowed_mime_types={"image/png"},
        )(fake)
