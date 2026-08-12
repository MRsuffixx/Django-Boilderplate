from django.conf import settings
from rest_framework import serializers

from apps.api_keys.models import APIKey


class APIKeySerializer(serializers.ModelSerializer):
    is_active = serializers.BooleanField(read_only=True)

    class Meta:
        model = APIKey
        fields = [
            "id",
            "name",
            "prefix",
            "scopes",
            "created_at",
            "last_used_at",
            "last_used_ip",
            "expires_at",
            "revoked_at",
            "is_active",
        ]
        read_only_fields = [
            "id",
            "prefix",
            "created_at",
            "last_used_at",
            "last_used_ip",
            "revoked_at",
            "is_active",
        ]

    def validate_scopes(self, value):
        unknown = set(value) - set(settings.API_KEY_AVAILABLE_SCOPES)
        if unknown:
            raise serializers.ValidationError(f"Unknown scopes: {', '.join(sorted(unknown))}")
        return sorted(set(value))

    def validate_expires_at(self, value):
        from django.utils import timezone

        if value and value <= timezone.now():
            raise serializers.ValidationError("Expiry must be in the future.")
        return value
