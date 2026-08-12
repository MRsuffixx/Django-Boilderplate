from django.conf import settings
from django.contrib.auth import logout, update_session_auth_hash
from rest_framework import permissions, status
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenRefreshView

from apps.api.serializers.accounts import UserSerializer
from apps.api.serializers.auth import (
    ChangeEmailSerializer,
    ChangePasswordSerializer,
    ChangeUsernameSerializer,
    EmailSerializer,
    LoginSerializer,
    LogoutSerializer,
    PasswordConfirmationSerializer,
    PasswordResetConfirmSerializer,
    RegistrationSerializer,
    TokenSerializer,
    TwoFactorCodeSerializer,
    TwoFactorDisableSerializer,
)
from apps.api.throttles import (
    EmailVerificationThrottle,
    LoginThrottle,
    PasswordResetThrottle,
    RegisterThrottle,
)
from apps.authentication.jwt import StatusAwareTokenRefreshSerializer
from apps.authentication.services import (
    AccountService,
    AuthenticationService,
    SessionService,
    TwoFactorService,
)
from apps.core.services import RuntimeSettingService
from common.exceptions import APIException
from common.responses import success_response


class RegisterView(APIView):
    permission_classes = [permissions.AllowAny]
    throttle_classes = [RegisterThrottle]

    def post(self, request):
        if not RuntimeSettingService.get("site.registration_enabled", True):
            raise APIException(
                "Registration is disabled.", code="REGISTRATION_DISABLED", status_code=403
            )
        serializer = RegistrationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = AccountService.register_user(**serializer.validated_data, request=request)
        return success_response(
            UserSerializer(user, context={"request": request}).data, status=status.HTTP_201_CREATED
        )


class LoginView(APIView):
    permission_classes = [permissions.AllowAny]
    throttle_classes = [LoginThrottle]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user, user_session = AuthenticationService.login(
            request=request, **serializer.validated_data
        )
        refresh = RefreshToken.for_user(user)
        return success_response(
            {
                "user": UserSerializer(user, context={"request": request}).data,
                "access": str(refresh.access_token),
                "refresh": str(refresh),
                "session_id": user_session.identifier,
            }
        )


class RefreshView(TokenRefreshView):
    permission_classes = [permissions.AllowAny]
    serializer_class = StatusAwareTokenRefreshSerializer

    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)
        return success_response(response.data, status=response.status_code)


class LogoutView(APIView):
    def post(self, request):
        serializer = LogoutSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        raw_refresh = serializer.validated_data.get("refresh")
        if raw_refresh:
            try:
                RefreshToken(raw_refresh).blacklist()
            except TokenError as exc:
                raise APIException("Invalid refresh token.", code="INVALID_TOKEN") from exc
        current = SessionService.current(request)
        if current:
            SessionService.revoke(current, actor=request.user, request=request)
        logout(request)
        return success_response({"logged_out": True})


class VerifyEmailView(APIView):
    permission_classes = [permissions.AllowAny]
    throttle_classes = [EmailVerificationThrottle]

    def post(self, request):
        serializer = TokenSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        AccountService.verify_email(raw_token=serializer.validated_data["token"], request=request)
        return success_response({"verified": True})


class ResendVerificationView(APIView):
    permission_classes = [permissions.AllowAny]
    throttle_classes = [EmailVerificationThrottle]

    def post(self, request):
        serializer = EmailSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        AccountService.resend_verification(email=serializer.validated_data["email"])
        return success_response({"message": "If eligible, a verification email will be sent."})


class PasswordResetRequestView(APIView):
    permission_classes = [permissions.AllowAny]
    throttle_classes = [PasswordResetThrottle]

    def post(self, request):
        serializer = EmailSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        AccountService.request_password_reset(email=serializer.validated_data["email"])
        return success_response({"message": "If eligible, a password reset email will be sent."})


class PasswordResetConfirmView(APIView):
    permission_classes = [permissions.AllowAny]
    throttle_classes = [PasswordResetThrottle]

    def post(self, request):
        serializer = PasswordResetConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        AccountService.reset_password(
            raw_token=serializer.validated_data["token"],
            new_password=serializer.validated_data["new_password"],
            request=request,
        )
        return success_response({"password_reset": True})


class ChangePasswordView(APIView):
    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        AccountService.change_password(
            user=request.user, request=request, **serializer.validated_data
        )
        request.user.refresh_from_db()
        update_session_auth_hash(request, request.user)
        return success_response({"password_changed": True})


class ChangeEmailView(APIView):
    def post(self, request):
        serializer = ChangeEmailSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        AccountService.request_email_change(user=request.user, **serializer.validated_data)
        return success_response(
            {"message": "A confirmation email will be sent to the new address."}
        )


class ConfirmEmailChangeView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = TokenSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        AccountService.confirm_email_change(
            raw_token=serializer.validated_data["token"], request=request
        )
        return success_response({"email_changed": True})


class ChangeUsernameView(APIView):
    def post(self, request):
        serializer = ChangeUsernameSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        user = AccountService.change_username(
            user=request.user, request=request, **serializer.validated_data
        )
        return success_response(UserSerializer(user, context={"request": request}).data)


class DeactivateAccountView(APIView):
    def post(self, request):
        serializer = PasswordConfirmationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        AccountService.deactivate(user=request.user, request=request, **serializer.validated_data)
        logout(request)
        return success_response({"deactivated": True})


class DeleteAccountRequestView(APIView):
    def post(self, request):
        serializer = PasswordConfirmationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        AccountService.request_deletion(user=request.user, **serializer.validated_data)
        return success_response({"message": "A deletion confirmation email will be sent."})


class DeleteAccountConfirmView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = TokenSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        AccountService.confirm_deletion(
            raw_token=serializer.validated_data["token"], request=request
        )
        return success_response({"deleted": True})


class TwoFactorSetupView(APIView):
    def post(self, request):
        if not settings.ENABLE_TWO_FACTOR:
            raise APIException(
                "Two-factor authentication is disabled.", code="FEATURE_DISABLED", status_code=404
            )
        secret, provisioning_uri = TwoFactorService.begin_setup(user=request.user)
        return success_response({"secret": secret, "provisioning_uri": provisioning_uri})


class TwoFactorConfirmView(APIView):
    def post(self, request):
        serializer = TwoFactorCodeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        codes = TwoFactorService.confirm_setup(
            user=request.user, request=request, **serializer.validated_data
        )
        return success_response({"enabled": True, "recovery_codes": codes})


class TwoFactorDisableView(APIView):
    def post(self, request):
        serializer = TwoFactorDisableSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        TwoFactorService.disable(user=request.user, request=request, **serializer.validated_data)
        return success_response({"disabled": True})


class RecoveryCodeRegenerateView(APIView):
    def post(self, request):
        serializer = TwoFactorCodeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        codes = TwoFactorService.regenerate_codes(
            user=request.user, request=request, **serializer.validated_data
        )
        return success_response({"recovery_codes": codes})
