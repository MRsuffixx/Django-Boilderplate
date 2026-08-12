from __future__ import annotations

from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from django.conf import settings
from rest_framework import serializers

from apps.accounts.models import User, UserPreferences, UserProfile
from apps.authorization.services import PermissionService
from apps.security.models import SecurityEvent


class UserSerializer(serializers.ModelSerializer):
    is_email_verified = serializers.BooleanField(read_only=True)
    is_phone_verified = serializers.BooleanField(read_only=True)
    display_name = serializers.CharField(read_only=True)
    permissions = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "username",
            "first_name",
            "last_name",
            "display_name",
            "avatar",
            "status",
            "is_email_verified",
            "is_phone_verified",
            "date_joined",
            "last_login",
            "created_at",
            "updated_at",
            "permissions",
        ]
        read_only_fields = fields

    def get_permissions(self, obj) -> list[str]:
        request = self.context.get("request")
        return sorted(PermissionService.permission_codes(obj)) if request and request.user == obj else []


class UserAdminSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "username",
            "first_name",
            "last_name",
            "status",
            "email_verified_at",
            "phone_verified_at",
            "is_active",
            "is_staff",
            "date_joined",
            "last_login",
            "last_login_ip",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "date_joined", "last_login", "last_login_ip", "created_at", "updated_at"]

    def validate_email(self, value):
        normalized = User.objects.normalize_email_address(value)
        query = User.objects.filter(email__iexact=normalized)
        if self.instance:
            query = query.exclude(pk=self.instance.pk)
        if query.exists():
            raise serializers.ValidationError("That email address is unavailable.")
        return normalized

    def validate_username(self, value):
        query = User.objects.filter(username__iexact=value.strip())
        if self.instance:
            query = query.exclude(pk=self.instance.pk)
        if query.exists():
            raise serializers.ValidationError("That username is unavailable.")
        return value.strip()


class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserProfile
        fields = ["id", "bio", "website", "location", "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]


class UserPreferencesSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserPreferences
        fields = ["id", "language", "timezone", "email_notifications", "security_emails", "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]

    def validate_language(self, value):
        supported = {code for code, _name in settings.LANGUAGES}
        if value not in supported:
            raise serializers.ValidationError("Unsupported language.")
        return value

    def validate_timezone(self, value):
        try:
            ZoneInfo(value)
        except ZoneInfoNotFoundError as exc:
            raise serializers.ValidationError("Unknown timezone.") from exc
        return value


class SecurityEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = SecurityEvent
        fields = ["id", "event_type", "ip_address", "user_agent", "request_id", "metadata", "created_at"]
        read_only_fields = fields
