from rest_framework import serializers

from apps.authorization.models import Permission, Role, RolePermission, UserPermissionOverride, UserRole


class PermissionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Permission
        fields = ["id", "codename", "description", "is_system", "created_at", "updated_at"]
        read_only_fields = ["id", "is_system", "created_at", "updated_at"]


class RoleSerializer(serializers.ModelSerializer):
    permissions = serializers.SlugRelatedField(many=True, read_only=True, slug_field="codename")

    class Meta:
        model = Role
        fields = ["id", "name", "slug", "description", "priority", "is_system", "permissions", "created_at", "updated_at"]
        read_only_fields = ["id", "is_system", "created_at", "updated_at"]


class RolePermissionSerializer(serializers.ModelSerializer):
    class Meta:
        model = RolePermission
        fields = ["id", "role", "permission", "created_at"]
        read_only_fields = ["id", "created_at"]


class UserRoleSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserRole
        fields = ["id", "user", "role", "granted_by", "valid_from", "valid_until", "created_at"]
        read_only_fields = ["id", "granted_by", "created_at"]


class UserPermissionOverrideSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserPermissionOverride
        fields = ["id", "user", "permission", "effect", "reason", "granted_by", "created_at", "updated_at"]
        read_only_fields = ["id", "granted_by", "created_at", "updated_at"]
