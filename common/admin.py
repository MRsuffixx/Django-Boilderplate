from __future__ import annotations

from apps.audit.services import AuditService


class AuditAdminMixin:
    """Record direct Django Admin writes without exposing sensitive field values."""

    def save_model(self, request, obj, form, change):
        before = {}
        if change:
            before = type(obj).objects.filter(pk=obj.pk).values().first() or {}
        super().save_model(request, obj, form, change)
        changed = form.changed_data or [field.name for field in obj._meta.fields]
        after = {field: getattr(obj, field, None) for field in changed}
        AuditService.record(
            action=f"admin.{obj._meta.label_lower}.{'updated' if change else 'created'}",
            target=obj,
            actor=request.user,
            request=request,
            before={field: before.get(field) for field in changed},
            after=after,
        )

    def delete_model(self, request, obj):
        AuditService.record(
            action=f"admin.{obj._meta.label_lower}.deleted",
            target=obj,
            actor=request.user,
            request=request,
        )
        super().delete_model(request, obj)

    def delete_queryset(self, request, queryset):
        for obj in queryset:
            AuditService.record(
                action=f"admin.{obj._meta.label_lower}.deleted",
                target=obj,
                actor=request.user,
                request=request,
            )
        super().delete_queryset(request, queryset)
