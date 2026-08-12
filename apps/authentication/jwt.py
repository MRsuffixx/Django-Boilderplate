from django.utils.translation import gettext_lazy as _
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import AuthenticationFailed
from rest_framework_simplejwt.serializers import TokenRefreshSerializer
from rest_framework_simplejwt.tokens import AccessToken

from apps.accounts.models import AccountStatus, User


def ensure_account_available(user) -> None:
    if not user.is_active or user.status != AccountStatus.ACTIVE:
        raise AuthenticationFailed(_("User account is unavailable."), code="user_inactive")


class StatusAwareJWTAuthentication(JWTAuthentication):
    def get_user(self, validated_token):
        user = super().get_user(validated_token)
        ensure_account_available(user)
        return user


class StatusAwareTokenRefreshSerializer(TokenRefreshSerializer):
    def validate(self, attrs):
        data = super().validate(attrs)
        access = AccessToken(data["access"])
        try:
            user = User.objects.get(pk=access["user_id"])
        except User.DoesNotExist as exc:
            raise AuthenticationFailed(_("User account is unavailable.")) from exc
        ensure_account_available(user)
        return data
