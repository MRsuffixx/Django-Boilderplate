from __future__ import annotations

from typing import Any

from apps.audit.models import AuditLog
from common.logging import sanitize
from common.utils.network import get_client_ip


class AuditService:
    @staticmethod
    def record(
        *,
        action: str,
        target: Any = None,
        actor=None,
        request=None,
        before: dict | None = None,
        after: dict | None = None,
        metadata: dict | None = None,
        target_type: str | None = None,
        target_id: str | None = None,
        target_repr: str | None = None,
    ) -> AuditLog:
        resolved_type = target_type or (
            f"{target._meta.app_label}.{target._meta.model_name}"
            if target is not None
            else "system"
        )
        return AuditLog.objects.create(
            actor=actor if actor and actor.is_authenticated else None,
            action=action,
            target_type=resolved_type,
            target_id=target_id if target_id is not None else str(getattr(target, "pk", "")),
            target_repr=(target_repr if target_repr is not None else str(target or ""))[:255],
            before=sanitize(before or {}),
            after=sanitize(after or {}),
            metadata=sanitize(metadata or {}),
            request_id=getattr(request, "request_id", "") if request else "",
            ip_address=get_client_ip(request) if request else None,
            user_agent=request.META.get("HTTP_USER_AGENT", "")[:2000] if request else "",
        )
