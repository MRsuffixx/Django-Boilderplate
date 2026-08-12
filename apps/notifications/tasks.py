from datetime import timedelta

from celery import shared_task
from django.conf import settings
from django.db.models import Q
from django.utils import timezone

from apps.notifications.models import Notification


@shared_task(name="apps.notifications.tasks.cleanup_notifications")
def cleanup_notifications() -> int:
    cutoff = timezone.now() - timedelta(days=settings.NOTIFICATION_RETENTION_DAYS)
    deleted, _ = Notification.objects.filter(
        Q(expires_at__lt=timezone.now()) | Q(created_at__lt=cutoff, read_at__isnull=False)
    ).delete()
    return deleted
