from __future__ import annotations

from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

from apps.accounts.models import User


class RegistrationSerializer(serializers.Serializer):
    email = serializers.EmailField()
    username = serializers.RegexField(r"^[\w.@+-]+$", max_length=150)
    password = serializers.CharField(write_only=True, trim_whitespace=False)
    first_name = serializers.CharField(max_length=150, required=False, allow_blank=True)
    last_name = serializers.CharField(max_length=150, required=False, allow_blank=True)

    def validate_email(self, value):
        normalized = User.objects.normalize_email_address(value)
        if User.objects.filter(email__iexact=normalized).exists():
            raise serializers.ValidationError("An account with those details already exists.")
        return normalized

    def validate_username(self, value):
        value = value.strip()
        if User.objects.filter(username__iexact=value).exists():
            raise serializers.ValidationError("An account with those details already exists.")
        return value

    def validate_password(self, value):
        validate_password(value)
        return value


class LoginSerializer(serializers.Serializer):
    identifier = serializers.CharField(max_length=254)
    password = serializers.CharField(write_only=True, trim_whitespace=False)
    code = serializers.CharField(max_length=32, required=False, allow_blank=True, write_only=True)
    remember_me = serializers.BooleanField(required=False, default=False)


class TokenSerializer(serializers.Serializer):
    token = serializers.CharField(write_only=True)


class EmailSerializer(serializers.Serializer):
    email = serializers.EmailField()


class PasswordResetConfirmSerializer(TokenSerializer):
    new_password = serializers.CharField(write_only=True, trim_whitespace=False)

    def validate_new_password(self, value):
        validate_password(value)
        return value


class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(write_only=True, trim_whitespace=False)
    new_password = serializers.CharField(write_only=True, trim_whitespace=False)


class ChangeEmailSerializer(serializers.Serializer):
    password = serializers.CharField(write_only=True, trim_whitespace=False)
    new_email = serializers.EmailField()


class ChangeUsernameSerializer(serializers.Serializer):
    username = serializers.RegexField(r"^[\w.@+-]+$", max_length=150)

    def validate_username(self, value):
        request = self.context["request"]
        value = value.strip()
        if User.objects.filter(username__iexact=value).exclude(pk=request.user.pk).exists():
            raise serializers.ValidationError("That username is unavailable.")
        return value


class PasswordConfirmationSerializer(serializers.Serializer):
    password = serializers.CharField(write_only=True, trim_whitespace=False)


class LogoutSerializer(serializers.Serializer):
    refresh = serializers.CharField(required=False, allow_blank=True, write_only=True)


class TwoFactorCodeSerializer(serializers.Serializer):
    code = serializers.CharField(max_length=32, trim_whitespace=True)


class TwoFactorSetupSerializer(serializers.Serializer):
    password = serializers.CharField(write_only=True, trim_whitespace=False)


class TwoFactorDisableSerializer(TwoFactorCodeSerializer):
    password = serializers.CharField(write_only=True, trim_whitespace=False)
