from django.conf import settings
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.api.views.accounts import (
    CurrentUserPreferencesView,
    CurrentUserProfileView,
    CurrentUserView,
    SecurityEventAdminViewSet,
    SecurityEventListView,
    UserAdminViewSet,
)
from apps.api.views.api_keys import APIKeyViewSet
from apps.api.views.auth import (
    ChangeEmailView,
    ChangePasswordView,
    ChangeUsernameView,
    ConfirmEmailChangeView,
    DeactivateAccountView,
    DeleteAccountConfirmView,
    DeleteAccountRequestView,
    LoginView,
    LogoutView,
    PasswordResetConfirmView,
    PasswordResetRequestView,
    RecoveryCodeRegenerateView,
    RefreshView,
    RegisterView,
    ResendVerificationView,
    TwoFactorConfirmView,
    TwoFactorDisableView,
    TwoFactorSetupView,
    VerifyEmailView,
)
from apps.api.views.authorization import (
    PermissionViewSet,
    RolePermissionViewSet,
    RoleViewSet,
    UserPermissionOverrideViewSet,
    UserRoleViewSet,
)
from apps.api.views.core import AuditLogViewSet, FeatureFlagViewSet, SettingViewSet
from apps.api.views.notifications import NotificationViewSet
from apps.api.views.sessions import UserSessionViewSet

router = DefaultRouter()
router.register("users", UserAdminViewSet, basename="user-admin")
router.register("users/me/sessions", UserSessionViewSet, basename="user-session")
if settings.ENABLE_NOTIFICATIONS:
    router.register("notifications", NotificationViewSet, basename="notification")
if settings.ENABLE_API_KEYS:
    router.register("api-keys", APIKeyViewSet, basename="api-key")
router.register("roles", RoleViewSet, basename="role")
router.register("permissions", PermissionViewSet, basename="permission")
router.register("role-permissions", RolePermissionViewSet, basename="role-permission")
router.register("user-roles", UserRoleViewSet, basename="user-role")
router.register(
    "permission-overrides", UserPermissionOverrideViewSet, basename="permission-override"
)
router.register("audit-logs", AuditLogViewSet, basename="audit-log")
router.register("security-events", SecurityEventAdminViewSet, basename="security-event-admin")
router.register("settings", SettingViewSet, basename="setting")
router.register("feature-flags", FeatureFlagViewSet, basename="feature-flag")

auth_patterns = [
    path("register/", RegisterView.as_view(), name="register"),
    path("login/", LoginView.as_view(), name="login"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("token/refresh/", RefreshView.as_view(), name="token-refresh"),
    path("verify-email/", VerifyEmailView.as_view(), name="verify-email"),
    path("resend-verification/", ResendVerificationView.as_view(), name="resend-verification"),
    path("password-reset/", PasswordResetRequestView.as_view(), name="password-reset"),
    path(
        "password-reset/confirm/", PasswordResetConfirmView.as_view(), name="password-reset-confirm"
    ),
    path("password/change/", ChangePasswordView.as_view(), name="password-change"),
    path("email/change/", ChangeEmailView.as_view(), name="email-change"),
    path("email/change/confirm/", ConfirmEmailChangeView.as_view(), name="email-change-confirm"),
    path("username/change/", ChangeUsernameView.as_view(), name="username-change"),
    path("account/deactivate/", DeactivateAccountView.as_view(), name="account-deactivate"),
    path("account/delete/", DeleteAccountRequestView.as_view(), name="account-delete"),
    path(
        "account/delete/confirm/", DeleteAccountConfirmView.as_view(), name="account-delete-confirm"
    ),
    path("2fa/setup/", TwoFactorSetupView.as_view(), name="two-factor-setup"),
    path("2fa/confirm/", TwoFactorConfirmView.as_view(), name="two-factor-confirm"),
    path("2fa/disable/", TwoFactorDisableView.as_view(), name="two-factor-disable"),
    path(
        "2fa/recovery-codes/regenerate/",
        RecoveryCodeRegenerateView.as_view(),
        name="recovery-codes-regenerate",
    ),
]

urlpatterns = [
    path("auth/", include(auth_patterns)),
    path("users/me/", CurrentUserView.as_view(), name="current-user"),
    path("users/me/profile/", CurrentUserProfileView.as_view(), name="current-user-profile"),
    path(
        "users/me/preferences/",
        CurrentUserPreferencesView.as_view(),
        name="current-user-preferences",
    ),
    path("users/me/security-events/", SecurityEventListView.as_view(), name="security-events"),
    path("", include(router.urls)),
]
