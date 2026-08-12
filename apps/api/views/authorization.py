from rest_framework import viewsets

from apps.api.serializers.authorization import (
    PermissionSerializer,
    RolePermissionSerializer,
    RoleSerializer,
    UserPermissionOverrideSerializer,
    UserRoleSerializer,
)
from apps.audit.services import AuditService
from apps.authorization.models import Permission, Role, RolePermission, UserPermissionOverride, UserRole
from common.permissions import HasPermission


class AuthorizationViewSet(viewsets.ModelViewSet):
    permission_classes = [HasPermission]
    required_permission = "roles.manage"
    audit_name = "authorization"

    def perform_create(self, serializer):
        instance = serializer.save(granted_by=self.request.user) if "granted_by" in serializer.fields else serializer.save()
        AuditService.record(action=f"{self.audit_name}.created", target=instance, actor=self.request.user, request=self.request, after=serializer.validated_data)

    def perform_update(self, serializer):
        before = {field: getattr(serializer.instance, field) for field in serializer.validated_data}
        instance = serializer.save()
        AuditService.record(action=f"{self.audit_name}.updated", target=instance, actor=self.request.user, request=self.request, before=before, after=serializer.validated_data)

    def perform_destroy(self, instance):
        AuditService.record(action=f"{self.audit_name}.deleted", target=instance, actor=self.request.user, request=self.request)
        instance.delete()


class RoleViewSet(AuthorizationViewSet):
    queryset = Role.objects.prefetch_related("permissions")
    serializer_class = RoleSerializer
    search_fields = ["name", "slug", "description"]
    ordering_fields = ["name", "priority", "created_at"]
    audit_name = "role"


class PermissionViewSet(AuthorizationViewSet):
    queryset = Permission.objects.all()
    serializer_class = PermissionSerializer
    search_fields = ["codename", "description"]
    ordering_fields = ["codename", "created_at"]
    audit_name = "permission"


class RolePermissionViewSet(AuthorizationViewSet):
    queryset = RolePermission.objects.select_related("role", "permission")
    serializer_class = RolePermissionSerializer
    filterset_fields = ["role", "permission"]
    audit_name = "role_permission"


class UserRoleViewSet(AuthorizationViewSet):
    queryset = UserRole.objects.select_related("user", "role", "granted_by")
    serializer_class = UserRoleSerializer
    filterset_fields = ["user", "role"]
    audit_name = "user_role"


class UserPermissionOverrideViewSet(AuthorizationViewSet):
    queryset = UserPermissionOverride.objects.select_related("user", "permission", "granted_by")
    serializer_class = UserPermissionOverrideSerializer
    filterset_fields = ["user", "permission", "effect"]
    audit_name = "user_permission_override"
