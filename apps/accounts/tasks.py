from celery import shared_task
from django.db.models import Q
from django.utils import timezone

from apps.accounts.models import AccountStatus, User


@shared_task(name="apps.accounts.tasks.expire_temporary_bans")
def expire_temporary_bans() -> int:
    now = timezone.now()
    user_ids = list(
        User.objects.filter(status=AccountStatus.BANNED, bans__expires_at__lte=now, bans__revoked_at__isnull=True)
        .values_list("pk", flat=True)
        .distinct()
    )
    updated = 0
    for user in User.objects.filter(pk__in=user_ids):
        has_active = user.bans.filter(revoked_at__isnull=True, starts_at__lte=now).filter(
            Q(expires_at__isnull=True) | Q(expires_at__gt=now)
        ).exists()
        if not has_active:
            user.status = AccountStatus.ACTIVE
            user.save(update_fields=["status", "updated_at"])
            updated += 1
    return updated
