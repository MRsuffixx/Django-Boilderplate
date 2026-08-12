from django.db.models import Q
from django.utils import timezone

from apps.accounts.models import AccountStatus, User
from apps.audit.services import AuditService
from apps.authentication.services import SessionService, TokenService
from common.tasks import shared_task


@shared_task(name="apps.accounts.tasks.expire_temporary_bans")
def expire_temporary_bans() -> int:
    now = timezone.now()
    activated = 0
    users_to_activate = (
        User.objects.exclude(status=AccountStatus.BANNED)
        .filter(
            bans__revoked_at__isnull=True,
            bans__starts_at__lte=now,
        )
        .filter(Q(bans__expires_at__isnull=True) | Q(bans__expires_at__gt=now))
        .distinct()
    )
    for user in users_to_activate:
        user.status = AccountStatus.BANNED
        user.save(update_fields=["status", "updated_at"])
        SessionService.revoke_all(user=user)
        TokenService.revoke_all_jwt(user=user)
        AuditService.record(action="account.ban_activated", target=user)
        activated += 1
    user_ids = list(
        User.objects.filter(
            status=AccountStatus.BANNED, bans__expires_at__lte=now, bans__revoked_at__isnull=True
        )
        .values_list("pk", flat=True)
        .distinct()
    )
    updated = 0
    for user in User.objects.filter(pk__in=user_ids):
        has_active = (
            user.bans.filter(revoked_at__isnull=True, starts_at__lte=now)
            .filter(Q(expires_at__isnull=True) | Q(expires_at__gt=now))
            .exists()
        )
        if not has_active:
            user.status = AccountStatus.ACTIVE
            user.save(update_fields=["status", "updated_at"])
            updated += 1
    return updated + activated
