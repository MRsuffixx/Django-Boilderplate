from rest_framework import viewsets

from apps.api.serializers.core import AuditLogSerializer, FeatureFlagSerializer, SettingSerializer
from apps.audit.models import AuditLog
from apps.audit.services import AuditService
from apps.core.models import FeatureFlag, Setting
from common.permissions import HasPermission


class AuditLogViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = AuditLog.objects.select_related("actor")
    serializer_class = AuditLogSerializer
    permission_classes = [HasPermission]
    required_permission = "audit.view"
    filterset_fields = ["action", "target_type", "actor"]
    search_fields = ["action", "target_repr", "target_id", "request_id"]
    ordering_fields = ["created_at", "action"]
    ordering = ["-created_at"]


class SettingViewSet(viewsets.ModelViewSet):
    queryset = Setting.objects.all()
    serializer_class = SettingSerializer
    permission_classes = [HasPermission]
    filterset_fields = ["group", "is_public", "value_type"]
    search_fields = ["key", "description"]

    @property
    def required_permission(self):
        return "settings.view" if self.action in {"list", "retrieve"} else "settings.update"

    def perform_create(self, serializer):
        row = serializer.save()
        row.full_clean()
        AuditService.record(
            action="setting.created",
            target=row,
            actor=self.request.user,
            request=self.request,
            after=serializer.validated_data,
        )

    def perform_update(self, serializer):
        before = {field: getattr(serializer.instance, field) for field in serializer.validated_data}
        row = serializer.save()
        row.full_clean()
        AuditService.record(
            action="setting.updated",
            target=row,
            actor=self.request.user,
            request=self.request,
            before=before,
            after=serializer.validated_data,
        )


class FeatureFlagViewSet(viewsets.ModelViewSet):
    queryset = FeatureFlag.objects.all()
    serializer_class = FeatureFlagSerializer
    permission_classes = [HasPermission]
    search_fields = ["key", "description"]

    @property
    def required_permission(self):
        return (
            "feature_flags.view" if self.action in {"list", "retrieve"} else "feature_flags.update"
        )

    def perform_create(self, serializer):
        row = serializer.save()
        AuditService.record(
            action="feature_flag.created",
            target=row,
            actor=self.request.user,
            request=self.request,
            after=serializer.validated_data,
        )

    def perform_update(self, serializer):
        before = {field: getattr(serializer.instance, field) for field in serializer.validated_data}
        row = serializer.save()
        AuditService.record(
            action="feature_flag.updated",
            target=row,
            actor=self.request.user,
            request=self.request,
            before=before,
            after=serializer.validated_data,
        )
