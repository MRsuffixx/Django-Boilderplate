from django.conf import settings
from django.contrib.auth import logout, update_session_auth_hash
from rest_framework import generics, permissions, status
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
    TwoFactorSetupSerializer,
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


class RegisterView(generics.GenericAPIView):
    serializer_class = RegistrationSerializer
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


class LoginView(generics.GenericAPIView):
    serializer_class = LoginSerializer
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


class LogoutView(generics.GenericAPIView):
    serializer_class = LogoutSerializer

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


class VerifyEmailView(generics.GenericAPIView):
    serializer_class = TokenSerializer
    permission_classes = [permissions.AllowAny]
    throttle_classes = [EmailVerificationThrottle]

    def post(self, request):
        serializer = TokenSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        AccountService.verify_email(raw_token=serializer.validated_data["token"], request=request)
        return success_response({"verified": True})


class ResendVerificationView(generics.GenericAPIView):
    serializer_class = EmailSerializer
    permission_classes = [permissions.AllowAny]
    throttle_classes = [EmailVerificationThrottle]

    def post(self, request):
        serializer = EmailSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        AccountService.resend_verification(email=serializer.validated_data["email"])
        return success_response({"message": "If eligible, a verification email will be sent."})


class PasswordResetRequestView(generics.GenericAPIView):
    serializer_class = EmailSerializer
    permission_classes = [permissions.AllowAny]
    throttle_classes = [PasswordResetThrottle]

    def post(self, request):
        serializer = EmailSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        AccountService.request_password_reset(email=serializer.validated_data["email"])
        return success_response({"message": "If eligible, a password reset email will be sent."})


class PasswordResetConfirmView(generics.GenericAPIView):
    serializer_class = PasswordResetConfirmSerializer
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


class ChangePasswordView(generics.GenericAPIView):
    serializer_class = ChangePasswordSerializer

    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        AccountService.change_password(
            user=request.user, request=request, **serializer.validated_data
        )
        request.user.refresh_from_db()
        update_session_auth_hash(request, request.user)
        return success_response({"password_changed": True})


class ChangeEmailView(generics.GenericAPIView):
    serializer_class = ChangeEmailSerializer

    def post(self, request):
        serializer = ChangeEmailSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        AccountService.request_email_change(user=request.user, **serializer.validated_data)
        return success_response(
            {"message": "A confirmation email will be sent to the new address."}
        )


class ConfirmEmailChangeView(generics.GenericAPIView):
    serializer_class = TokenSerializer
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = TokenSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        AccountService.confirm_email_change(
            raw_token=serializer.validated_data["token"], request=request
        )
        return success_response({"email_changed": True})


class ChangeUsernameView(generics.GenericAPIView):
    serializer_class = ChangeUsernameSerializer

    def post(self, request):
        serializer = ChangeUsernameSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        user = AccountService.change_username(
            user=request.user, request=request, **serializer.validated_data
        )
        return success_response(UserSerializer(user, context={"request": request}).data)


class DeactivateAccountView(generics.GenericAPIView):
    serializer_class = PasswordConfirmationSerializer

    def post(self, request):
        serializer = PasswordConfirmationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        AccountService.deactivate(user=request.user, request=request, **serializer.validated_data)
        logout(request)
        return success_response({"deactivated": True})


class DeleteAccountRequestView(generics.GenericAPIView):
    serializer_class = PasswordConfirmationSerializer

    def post(self, request):
        serializer = PasswordConfirmationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        AccountService.request_deletion(user=request.user, **serializer.validated_data)
        return success_response({"message": "A deletion confirmation email will be sent."})


class DeleteAccountConfirmView(generics.GenericAPIView):
    serializer_class = TokenSerializer
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = TokenSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        AccountService.confirm_deletion(
            raw_token=serializer.validated_data["token"], request=request
        )
        return success_response({"deleted": True})


class TwoFactorSetupView(generics.GenericAPIView):
    serializer_class = TwoFactorSetupSerializer

    def post(self, request):
        if not settings.ENABLE_TWO_FACTOR:
            raise APIException(
                "Two-factor authentication is disabled.", code="FEATURE_DISABLED", status_code=404
            )
        serializer = TwoFactorSetupSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        secret, provisioning_uri = TwoFactorService.begin_setup(
            user=request.user, **serializer.validated_data
        )
        return success_response({"secret": secret, "provisioning_uri": provisioning_uri})


class TwoFactorConfirmView(generics.GenericAPIView):
    serializer_class = TwoFactorCodeSerializer

    def post(self, request):
        serializer = TwoFactorCodeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        codes = TwoFactorService.confirm_setup(
            user=request.user, request=request, **serializer.validated_data
        )
        return success_response({"enabled": True, "recovery_codes": codes})


class TwoFactorDisableView(generics.GenericAPIView):
    serializer_class = TwoFactorDisableSerializer

    def post(self, request):
        serializer = TwoFactorDisableSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        TwoFactorService.disable(user=request.user, request=request, **serializer.validated_data)
        return success_response({"disabled": True})


class RecoveryCodeRegenerateView(generics.GenericAPIView):
    serializer_class = TwoFactorCodeSerializer

    def post(self, request):
        serializer = TwoFactorCodeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        codes = TwoFactorService.regenerate_codes(
            user=request.user, request=request, **serializer.validated_data
        )
        return success_response({"recovery_codes": codes})
