from __future__ import annotations

from django.db.models import Q
from django.utils import timezone

from apps.authorization.models import OverrideEffect, UserPermissionOverride


class PermissionService:
    """Resolve permissions: account gate -> explicit DENY -> ALLOW -> superuser -> active roles."""

    @staticmethod
    def has_permission(user, codename: str) -> bool:
        if not user or not user.is_authenticated or not user.can_authenticate_now():
            return False
        override = (
            UserPermissionOverride.objects.filter(user=user, permission__codename=codename)
            .values_list("effect", flat=True)
            .first()
        )
        if override == OverrideEffect.DENY:
            return False
        if override == OverrideEffect.ALLOW:
            return True
        if user.is_superuser:
            return True
        now = timezone.now()
        return (
            user.role_assignments.filter(
                valid_from__lte=now,
                role__permissions__codename=codename,
            )
            .filter(Q(valid_until__isnull=True) | Q(valid_until__gt=now))
            .exists()
        )

    @staticmethod
    def permission_codes(user) -> set[str]:
        if not user or not user.is_authenticated or not user.can_authenticate_now():
            return set()
        now = timezone.now()
        role_codes = set(
            user.role_assignments.filter(valid_from__lte=now)
            .filter(Q(valid_until__isnull=True) | Q(valid_until__gt=now))
            .values_list("role__permissions__codename", flat=True)
        )
        overrides = dict(user.permission_overrides.values_list("permission__codename", "effect"))
        if user.is_superuser:
            from apps.authorization.models import Permission

            role_codes = set(Permission.objects.values_list("codename", flat=True))
        role_codes.update(
            code for code, effect in overrides.items() if effect == OverrideEffect.ALLOW
        )
        role_codes.difference_update(
            code for code, effect in overrides.items() if effect == OverrideEffect.DENY
        )
        return role_codes
