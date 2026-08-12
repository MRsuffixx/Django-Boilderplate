from rest_framework import serializers

from apps.audit.models import AuditLog
from apps.core.models import FeatureFlag, Setting


class AuditLogSerializer(serializers.ModelSerializer):
    actor = serializers.StringRelatedField()

    class Meta:
        model = AuditLog
        fields = [
            "id",
            "actor",
            "action",
            "target_type",
            "target_id",
            "target_repr",
            "before",
            "after",
            "metadata",
            "request_id",
            "ip_address",
            "user_agent",
            "created_at",
        ]
        read_only_fields = fields


class SettingSerializer(serializers.ModelSerializer):
    class Meta:
        model = Setting
        fields = [
            "id",
            "key",
            "value",
            "value_type",
            "group",
            "is_public",
            "description",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def validate(self, attrs):
        instance = self.instance or Setting()
        for field, value in attrs.items():
            setattr(instance, field, value)
        instance.full_clean(exclude={"id"}, validate_unique=False)
        return attrs


class FeatureFlagSerializer(serializers.ModelSerializer):
    class Meta:
        model = FeatureFlag
        fields = ["id", "key", "enabled", "description", "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]
