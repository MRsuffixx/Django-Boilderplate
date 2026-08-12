from datetime import timedelta

from celery import shared_task
from django.conf import settings
from django.utils import timezone
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken, OutstandingToken

from apps.authentication.models import OneTimeToken, UserSession


@shared_task(name="apps.authentication.tasks.cleanup_sessions")
def cleanup_sessions() -> int:
    cutoff = timezone.now() - timedelta(days=settings.SESSION_RETENTION_DAYS)
    deleted, _ = UserSession.objects.filter(revoked_at__lt=cutoff).delete()
    return deleted


@shared_task(name="apps.authentication.tasks.cleanup_tokens")
def cleanup_tokens() -> int:
    cutoff = timezone.now() - timedelta(days=settings.TOKEN_RETENTION_DAYS)
    one_time, _ = OneTimeToken.objects.filter(expires_at__lt=cutoff).delete()
    expired_outstanding = OutstandingToken.objects.filter(expires_at__lt=timezone.now())
    blacklisted, _ = BlacklistedToken.objects.filter(token__in=expired_outstanding).delete()
    outstanding, _ = expired_outstanding.delete()
    return one_time + blacklisted + outstanding
