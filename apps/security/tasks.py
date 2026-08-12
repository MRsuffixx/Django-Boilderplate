from django.utils import timezone

from apps.security.models import LoginThrottleState
from common.tasks import shared_task


@shared_task(name="apps.security.tasks.cleanup_login_attempts")
def cleanup_login_attempts() -> int:
    deleted, _ = LoginThrottleState.objects.filter(expires_at__lt=timezone.now()).delete()
    return deleted
