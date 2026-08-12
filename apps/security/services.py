from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass
from datetime import timedelta

from django.conf import settings
from django.core.cache import cache
from django.db.models import Q
from django.utils import timezone

from apps.security.models import SecurityEvent, SecurityEventType
from common.utils.network import get_client_ip

logger = logging.getLogger(__name__)


class SecurityEventService:
    @staticmethod
    def record(
        event_type: str, *, user=None, request=None, metadata: dict | None = None
    ) -> SecurityEvent:
        return SecurityEvent.objects.create(
            user=user,
            event_type=event_type,
            ip_address=get_client_ip(request) if request else None,
            user_agent=request.META.get("HTTP_USER_AGENT", "")[:2000] if request else "",
            request_id=getattr(request, "request_id", "") if request else "",
            metadata=metadata or {},
        )


@dataclass(frozen=True, slots=True)
class LockoutState:
    locked: bool
    retry_after: int = 0
    account_locked: bool = False


class LoginProtectionService:
    namespace = "login-protection"

    @classmethod
    def _digest(cls, value: str) -> str:
        return hashlib.sha256(value.strip().casefold().encode()).hexdigest()

    @classmethod
    def _dimensions(cls, identifier: str, ip_address: str | None) -> list[str]:
        identifier_hash = cls._digest(identifier)
        ip_hash = cls._digest(ip_address or "unknown")
        return [f"id:{identifier_hash}", f"ip:{ip_hash}", f"combo:{identifier_hash}:{ip_hash}"]

    @classmethod
    def check(cls, identifier: str, ip_address: str | None) -> LockoutState:
        retry_after = 0
        for dimension in cls._dimensions(identifier, ip_address):
            ttl = cache.ttl(f"{cls.namespace}:lock:{dimension}") if hasattr(cache, "ttl") else None
            if cache.get(f"{cls.namespace}:lock:{dimension}"):
                retry_after = max(retry_after, ttl or settings.LOGIN_LOCKOUT_SECONDS)
        return LockoutState(bool(retry_after), retry_after)

    @classmethod
    def register_failure(cls, identifier: str, ip_address: str | None) -> LockoutState:
        longest = 0
        account_longest = 0
        for dimension in cls._dimensions(identifier, ip_address):
            attempts_key = f"{cls.namespace}:attempts:{dimension}"
            if cache.add(attempts_key, 1, timeout=settings.LOGIN_MAX_BACKOFF_SECONDS):
                attempts = 1
            else:
                try:
                    attempts = cache.incr(attempts_key)
                except ValueError:
                    cache.set(attempts_key, 1, timeout=settings.LOGIN_MAX_BACKOFF_SECONDS)
                    attempts = 1
            if attempts >= settings.LOGIN_MAX_ATTEMPTS:
                exponent = min(attempts - settings.LOGIN_MAX_ATTEMPTS, 6)
                lock_seconds = min(
                    settings.LOGIN_LOCKOUT_SECONDS * (2**exponent),
                    settings.LOGIN_MAX_BACKOFF_SECONDS,
                )
                cache.set(f"{cls.namespace}:lock:{dimension}", True, timeout=lock_seconds)
                longest = max(longest, lock_seconds)
                if dimension.startswith("id:"):
                    account_longest = max(account_longest, lock_seconds)
        return LockoutState(bool(longest), longest, bool(account_longest))

    @classmethod
    def reset(cls, identifier: str, ip_address: str | None) -> None:
        keys = []
        for dimension in cls._dimensions(identifier, ip_address):
            keys.extend(
                [f"{cls.namespace}:attempts:{dimension}", f"{cls.namespace}:lock:{dimension}"]
            )
        cache.delete_many(keys)

    @classmethod
    def lock_known_account(cls, *, identifier: str, retry_after: int, request=None) -> None:
        from apps.accounts.models import User, UserPreferences, UserSecuritySettings
        from common.services.email import EmailService

        user = User.objects.filter(
            Q(email__iexact=identifier.strip()) | Q(username__iexact=identifier.strip())
        ).first()
        if not user:
            return
        security_settings, _ = UserSecuritySettings.objects.get_or_create(user=user)
        was_locked = security_settings.is_locked
        security_settings.locked_until = timezone.now() + timedelta(seconds=retry_after)
        security_settings.save(update_fields=["locked_until", "updated_at"])
        if was_locked:
            return
        SecurityEventService.record(SecurityEventType.ACCOUNT_LOCKED, user=user, request=request)
        preferences, _ = UserPreferences.objects.get_or_create(user=user)
        if preferences.security_emails:
            EmailService.enqueue(
                template="account_locked",
                recipient=user.email,
                subject="Your account was temporarily locked",
                context={"user": user, "retry_after": retry_after},
            )
