from __future__ import annotations

import secrets

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from apps.api_keys.models import APIKey
from apps.audit.services import AuditService
from apps.security.models import SecurityEventType
from apps.security.services import SecurityEventService
from common.crypto import keyed_hash, secure_compare


class APIKeyService:
    marker = "dk"

    @classmethod
    def _hash(cls, raw_key: str) -> str:
        return keyed_hash(
            raw_key, purpose="api-key", pepper=settings.API_KEY_PEPPER or settings.SECRET_KEY
        )

    @classmethod
    @transaction.atomic
    def create(
        cls, *, owner, name: str, scopes: list[str], expires_at=None, actor=None, request=None
    ) -> tuple[APIKey, str]:
        prefix = secrets.token_hex(6)
        secret = secrets.token_urlsafe(32)
        raw = f"{cls.marker}_{prefix}.{secret}"
        api_key = APIKey.objects.create(
            owner=owner,
            name=name,
            prefix=prefix,
            key_hash=cls._hash(raw),
            scopes=sorted(set(scopes)),
            expires_at=expires_at,
        )
        SecurityEventService.record(
            SecurityEventType.API_KEY_CREATED,
            user=owner,
            request=request,
            metadata={"prefix": prefix},
        )
        AuditService.record(
            action="api_key.created",
            target=api_key,
            actor=actor or owner,
            request=request,
            after={"name": name, "scopes": api_key.scopes, "prefix": prefix},
        )
        return api_key, raw

    @classmethod
    def authenticate(cls, raw_key: str, *, ip_address=None) -> APIKey | None:
        if not raw_key.startswith(f"{cls.marker}_") or "." not in raw_key:
            return None
        prefix = raw_key.split("_", 1)[1].split(".", 1)[0]
        key = APIKey.objects.select_related("owner").filter(prefix=prefix).first()
        if (
            not key
            or not key.is_active
            or not key.owner.can_authenticate_now()
            or not secure_compare(key.key_hash, cls._hash(raw_key))
        ):
            return None
        APIKey.objects.filter(pk=key.pk).update(
            last_used_at=timezone.now(), last_used_ip=ip_address
        )
        return key

    @staticmethod
    @transaction.atomic
    def revoke(*, api_key: APIKey, actor=None, request=None) -> None:
        locked = APIKey.objects.select_for_update().get(pk=api_key.pk)
        if locked.revoked_at:
            return
        locked.revoked_at = timezone.now()
        locked.save(update_fields=["revoked_at"])
        SecurityEventService.record(
            SecurityEventType.API_KEY_REVOKED,
            user=locked.owner,
            request=request,
            metadata={"prefix": locked.prefix},
        )
        AuditService.record(
            action="api_key.revoked",
            target=locked,
            actor=actor or locked.owner,
            request=request,
            after={"revoked_at": locked.revoked_at.isoformat()},
        )
