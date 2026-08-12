from datetime import timedelta

from celery import shared_task
from django.conf import settings
from django.utils import timezone

from apps.audit.models import AuditLog


@shared_task(name="apps.audit.tasks.cleanup_audit_logs")
def cleanup_audit_logs() -> int:
    if settings.AUDIT_RETENTION_DAYS <= 0:
        return 0
    cutoff = timezone.now() - timedelta(days=settings.AUDIT_RETENTION_DAYS)
    deleted, _ = AuditLog.objects.filter(created_at__lt=cutoff).hard_delete_for_retention()
    return deleted
