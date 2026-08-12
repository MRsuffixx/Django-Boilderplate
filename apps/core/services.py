from __future__ import annotations

from django.core.cache import cache

from apps.core.models import FeatureFlag, Setting


class RuntimeSettingService:
    cache_timeout = 300

    @classmethod
    def get(cls, key: str, default=None, *, public_only: bool = False):
        cache_key = f"runtime-setting:{key}:{int(public_only)}"
        cached = cache.get(cache_key, default=None)
        if cached is not None:
            return cached
        query = Setting.objects.filter(key=key)
        if public_only:
            query = query.filter(is_public=True)
        row = query.first()
        value = row.value if row else default
        cache.set(cache_key, value, cls.cache_timeout)
        return value

    @classmethod
    def set(cls, *, key: str, value, value_type: str, actor=None, **defaults) -> Setting:
        from apps.audit.services import AuditService

        row, created = Setting.objects.update_or_create(
            key=key,
            defaults={"value": value, "value_type": value_type, **defaults},
        )
        row.full_clean()
        row.save()
        cache.delete(f"runtime-setting:{key}:0")
        cache.delete(f"runtime-setting:{key}:1")
        AuditService.record(action="setting.created" if created else "setting.updated", target=row, actor=actor)
        return row


class FeatureFlagService:
    @staticmethod
    def is_enabled(key: str, *, default: bool = False) -> bool:
        return FeatureFlag.objects.filter(key=key).values_list("enabled", flat=True).first() or default
