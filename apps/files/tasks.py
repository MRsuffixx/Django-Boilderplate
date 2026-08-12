from datetime import timedelta

from django.conf import settings
from django.utils import timezone

from apps.files.models import FileStatus, StoredFile
from common.tasks import shared_task


@shared_task(name="apps.files.tasks.cleanup_unused_files")
def cleanup_unused_files() -> int:
    cutoff = timezone.now() - timedelta(days=settings.FILE_RETENTION_DAYS)
    files = StoredFile.objects.filter(
        status=FileStatus.PENDING, created_at__lt=cutoff, deleted_at__isnull=True
    )
    count = 0
    for stored_file in files.iterator():
        stored_file.file.delete(save=False)
        stored_file.deleted_at = timezone.now()
        stored_file.save(update_fields=["deleted_at"])
        count += 1
    return count
