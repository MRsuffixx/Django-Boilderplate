from __future__ import annotations

from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from apps.accounts.models import AccountStatus, User, UserBan
from apps.audit.services import AuditService
from apps.authentication.services import SessionService, TokenService


class BanService:
    @staticmethod
    @transaction.atomic
    def ban(
        *, user: User, reason: str, actor=None, starts_at=None, expires_at=None, request=None
    ) -> UserBan:
        locked = User.objects.select_for_update().get(pk=user.pk)
        ban = UserBan.objects.create(
            user=locked,
            reason=reason,
            banned_by=actor,
            starts_at=starts_at or timezone.now(),
            expires_at=expires_at,
        )
        if ban.starts_at <= timezone.now():
            locked.status = AccountStatus.BANNED
            locked.save(update_fields=["status", "updated_at"])
            SessionService.revoke_all(user=locked, actor=actor, request=request)
            TokenService.revoke_all_jwt(user=locked)
        AuditService.record(
            action="account.banned",
            target=locked,
            actor=actor,
            request=request,
            after={"reason": reason, "expires_at": expires_at.isoformat() if expires_at else None},
        )
        return ban

    @staticmethod
    @transaction.atomic
    def revoke(*, ban: UserBan, actor=None, request=None) -> None:
        locked = UserBan.objects.select_for_update().select_related("user").get(pk=ban.pk)
        if locked.revoked_at:
            return
        locked.revoked_at = timezone.now()
        locked.save(update_fields=["revoked_at"])
        still_banned = (
            locked.user.bans.filter(revoked_at__isnull=True, starts_at__lte=timezone.now())
            .filter(Q(expires_at__isnull=True) | Q(expires_at__gt=timezone.now()))
            .exists()
        )
        if not still_banned and locked.user.status == AccountStatus.BANNED:
            locked.user.status = AccountStatus.ACTIVE
            locked.user.save(update_fields=["status", "updated_at"])
        AuditService.record(
            action="account.ban_revoked", target=locked.user, actor=actor, request=request
        )
