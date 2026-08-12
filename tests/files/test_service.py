import io

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image

from apps.files.models import FileStatus
from apps.files.services import FileService
from apps.files.validators import SecureFileValidator

pytestmark = pytest.mark.django_db


def test_file_service_stores_validated_metadata_with_randomized_path(user):
    content = io.BytesIO()
    Image.new("RGB", (5, 5), color="blue").save(content, format="PNG")
    upload = SimpleUploadedFile("client-name.png", content.getvalue(), content_type="image/png")

    stored = FileService.store(
        owner=user,
        uploaded_file=upload,
        validator=SecureFileValidator(
            allowed_extensions={"png"},
            allowed_mime_types={"image/png"},
        ),
    )

    assert stored.status == FileStatus.READY
    assert stored.original_name == "client-name.png"
    assert "client-name" not in stored.file.name
    assert stored.file.name.startswith(f"uploads/{user.pk}/")
