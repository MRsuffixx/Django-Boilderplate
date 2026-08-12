from __future__ import annotations

import logging
import secrets
from datetime import timedelta

import pyotp
from django.conf import settings
from django.contrib.auth import authenticate, login
from django.contrib.auth.password_validation import validate_password
from django.contrib.sessions.models import Session
from django.db import IntegrityError, transaction
from django.db.models import Q
from django.utils import timezone
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken, OutstandingToken
from user_agents import parse as parse_user_agent

from apps.accounts.models import (
    AccountStatus,
    User,
    UserPreferences,
    UserProfile,
    UserSecuritySettings,
)
from apps.audit.services import AuditService
from apps.authentication.models import (
    OneTimeToken,
    RecoveryCode,
    TokenPurpose,
    TwoFactorCredential,
    UserSession,
)
from apps.authorization.models import Role, UserRole
from apps.security.models import SecurityEventType
from apps.security.services import LoginProtectionService, SecurityEventService
from common.crypto import decrypt_value, encrypt_value, generate_token, keyed_hash
from common.events import ApplicationEvent, EventBus
from common.exceptions import APIException
from common.services.email import EmailService
from common.utils.network import get_client_ip

logger = logging.getLogger(__name__)


class TokenService:
    @staticmethod
    @transaction.atomic
    def issue(*, user: User, purpose: str, ttl: timedelta, metadata: dict | None = None) -> str:
        now = timezone.now()
        OneTimeToken.objects.filter(user=user, purpose=purpose, used_at__isnull=True).update(
            used_at=now
        )
        raw = generate_token()
        OneTimeToken.objects.create(
            user=user,
            purpose=purpose,
            token_hash=keyed_hash(raw, purpose=f"one-time:{purpose}"),
            metadata=metadata or {},
            expires_at=now + ttl,
        )
        return raw

    @staticmethod
    @transaction.atomic
    def consume(*, raw_token: str, purpose: str) -> OneTimeToken:
        token_hash = keyed_hash(raw_token, purpose=f"one-time:{purpose}")
        try:
            token = (
                OneTimeToken.objects.select_for_update()
                .select_related("user")
                .get(
                    token_hash=token_hash,
                    purpose=purpose,
                )
            )
        except OneTimeToken.DoesNotExist as exc:
            raise APIException("This token is invalid or expired.", code="INVALID_TOKEN") from exc
        if not token.is_usable:
            raise APIException("This token is invalid or expired.", code="INVALID_TOKEN")
        token.used_at = timezone.now()
        token.save(update_fields=["used_at"])
        return token

    @staticmethod
    def revoke_all_jwt(*, user: User) -> int:
        created = 0
        for outstanding in OutstandingToken.objects.filter(user=user):
            _, was_created = BlacklistedToken.objects.get_or_create(token=outstanding)
            created += int(was_created)
        return created


class SessionService:
    @staticmethod
    def _hash(session_key: str) -> str:
        return keyed_hash(session_key, purpose="django-session")

    @classmethod
    @transaction.atomic
    def register(cls, *, user: User, request) -> tuple[UserSession, bool]:
        if not request.session.session_key:
            request.session.save()
        session_key = request.session.session_key
        key_hash = cls._hash(session_key)
        agent_text = request.META.get("HTTP_USER_AGENT", "")[:2000]
        agent = parse_user_agent(agent_text)
        device = (
            "mobile"
            if agent.is_mobile
            else "tablet"
            if agent.is_tablet
            else "pc"
            if agent.is_pc
            else "other"
        )
        existing_device = UserSession.objects.filter(
            user=user,
            user_agent=agent_text,
            revoked_at__isnull=True,
        ).exists()
        user_session, _ = UserSession.objects.update_or_create(
            session_key_hash=key_hash,
            defaults={
                "user": user,
                "identifier": secrets.token_hex(16),
                "encrypted_session_key": encrypt_value(session_key, purpose="django-session"),
                "ip_address": get_client_ip(request),
                "user_agent": agent_text,
                "browser": f"{agent.browser.family} {agent.browser.version_string}".strip(),
                "operating_system": f"{agent.os.family} {agent.os.version_string}".strip(),
                "device": device,
                "revoked_at": None,
            },
        )
        return user_session, not existing_device

    @classmethod
    def current(cls, request) -> UserSession | None:
        session = getattr(request, "session", None)
        key = getattr(session, "session_key", None)
        if not key:
            return None
        return UserSession.objects.filter(session_key_hash=cls._hash(key)).first()

    @classmethod
    @transaction.atomic
    def revoke(cls, session: UserSession, *, actor=None, request=None) -> None:
        locked = UserSession.objects.select_for_update().get(pk=session.pk)
        if locked.revoked_at:
            return
        locked.revoked_at = timezone.now()
        locked.save(update_fields=["revoked_at"])
        try:
            session_key = decrypt_value(locked.encrypted_session_key, purpose="django-session")
            Session.objects.filter(session_key=session_key).delete()
        except ValueError:
            logger.warning(
                "session.encrypted_reference_invalid",
                extra={"user_id": str(locked.user_id), "session_id": str(locked.pk)},
            )
        SecurityEventService.record(
            SecurityEventType.SESSION_REVOKED,
            user=locked.user,
            request=request,
            metadata={"session_identifier": locked.identifier},
        )
        AuditService.record(
            action="session.revoked",
            target=locked,
            actor=actor,
            request=request,
            after={"revoked_at": locked.revoked_at.isoformat()},
        )

    @classmethod
    def revoke_all(
        cls, *, user: User, actor=None, request=None, exclude_current: bool = False
    ) -> int:
        sessions = UserSession.objects.filter(user=user, revoked_at__isnull=True)
        current = cls.current(request) if request else None
        if exclude_current and current:
            sessions = sessions.exclude(pk=current.pk)
        session_list = list(sessions)
        for user_session in session_list:
            cls.revoke(user_session, actor=actor, request=request)
        return len(session_list)


class TwoFactorService:
    recovery_code_count = 10

    @staticmethod
    def _recovery_hash(code: str) -> str:
        return keyed_hash(code.strip().upper(), purpose="recovery-code")

    @classmethod
    @transaction.atomic
    def begin_setup(cls, *, user: User, password: str) -> tuple[str, str]:
        if not user.check_password(password):
            raise APIException(
                "Authentication failed.", code="AUTHENTICATION_FAILED", status_code=401
            )
        TwoFactorCredential.objects.filter(user=user, confirmed_at__isnull=True).delete()
        if TwoFactorCredential.objects.filter(
            user=user, confirmed_at__isnull=False, disabled_at__isnull=True
        ).exists():
            raise APIException(
                "Two-factor authentication is already enabled.", code="CONFLICT", status_code=409
            )
        secret = pyotp.random_base32()
        TwoFactorCredential.objects.create(
            user=user,
            encrypted_secret=encrypt_value(secret, purpose="totp-secret"),
        )
        uri = pyotp.TOTP(secret).provisioning_uri(name=user.email, issuer_name=settings.SITE_NAME)
        return secret, uri

    @classmethod
    @transaction.atomic
    def confirm_setup(cls, *, user: User, code: str, request=None) -> list[str]:
        try:
            credential = TwoFactorCredential.objects.select_for_update().get(
                user=user, confirmed_at__isnull=True
            )
        except TwoFactorCredential.DoesNotExist as exc:
            raise APIException(
                "No pending two-factor setup exists.", code="RESOURCE_NOT_FOUND", status_code=404
            ) from exc
        secret = decrypt_value(credential.encrypted_secret, purpose="totp-secret")
        if not pyotp.TOTP(secret).verify(code, valid_window=1):
            raise APIException(
                "The authentication code is invalid.", code="AUTHENTICATION_FAILED", status_code=401
            )
        credential.confirmed_at = timezone.now()
        credential.disabled_at = None
        credential.save(update_fields=["confirmed_at", "disabled_at"])
        codes = cls._replace_recovery_codes(credential)
        SecurityEventService.record(
            SecurityEventType.TWO_FACTOR_ENABLED, user=user, request=request
        )
        AuditService.record(action="two_factor.enabled", target=user, actor=user, request=request)
        transaction.on_commit(
            lambda: EmailService.enqueue(
                template="two_factor_enabled",
                recipient=user.email,
                subject=f"Two-factor authentication enabled on {settings.SITE_NAME}",
                context={"user": user},
            )
        )
        return codes

    @classmethod
    def verify(cls, *, user: User, code: str) -> tuple[bool, bool]:
        credential = TwoFactorCredential.objects.filter(user=user).first()
        if credential is None:
            return False, False
        if not credential.is_enabled:
            return False, False
        normalized = code.strip().replace("-", "").upper()
        secret = decrypt_value(credential.encrypted_secret, purpose="totp-secret")
        if pyotp.TOTP(secret).verify(normalized, valid_window=1):
            return True, False
        return cls._consume_recovery_code(credential, normalized), True

    @classmethod
    @transaction.atomic
    def _consume_recovery_code(cls, credential: TwoFactorCredential, code: str) -> bool:
        code_hash = cls._recovery_hash(code)
        recovery = (
            RecoveryCode.objects.select_for_update()
            .filter(credential=credential, code_hash=code_hash, used_at__isnull=True)
            .first()
        )
        if not recovery:
            return False
        recovery.used_at = timezone.now()
        recovery.save(update_fields=["used_at"])
        SecurityEventService.record(SecurityEventType.RECOVERY_CODE_USED, user=credential.user)
        return True

    @classmethod
    def _replace_recovery_codes(cls, credential: TwoFactorCredential) -> list[str]:
        credential.recovery_codes.all().delete()
        codes = [secrets.token_hex(5).upper() for _ in range(cls.recovery_code_count)]
        RecoveryCode.objects.bulk_create(
            [
                RecoveryCode(credential=credential, code_hash=cls._recovery_hash(code))
                for code in codes
            ]
        )
        return codes

    @classmethod
    @transaction.atomic
    def regenerate_codes(cls, *, user: User, code: str, request=None) -> list[str]:
        valid, _ = cls.verify(user=user, code=code)
        if not valid:
            raise APIException(
                "The authentication code is invalid.", code="AUTHENTICATION_FAILED", status_code=401
            )
        credential = TwoFactorCredential.objects.select_for_update().get(
            user=user, disabled_at__isnull=True
        )
        codes = cls._replace_recovery_codes(credential)
        AuditService.record(
            action="two_factor.recovery_codes_regenerated", target=user, actor=user, request=request
        )
        return codes

    @classmethod
    @transaction.atomic
    def disable(cls, *, user: User, password: str, code: str, request=None) -> None:
        if not user.check_password(password):
            raise APIException(
                "Authentication failed.", code="AUTHENTICATION_FAILED", status_code=401
            )
        valid, _ = cls.verify(user=user, code=code)
        if not valid:
            raise APIException(
                "The authentication code is invalid.", code="AUTHENTICATION_FAILED", status_code=401
            )
        credential = TwoFactorCredential.objects.select_for_update().get(user=user)
        credential.disabled_at = timezone.now()
        credential.save(update_fields=["disabled_at"])
        credential.recovery_codes.filter(used_at__isnull=True).update(used_at=timezone.now())
        SecurityEventService.record(
            SecurityEventType.TWO_FACTOR_DISABLED, user=user, request=request
        )
        AuditService.record(action="two_factor.disabled", target=user, actor=user, request=request)
        transaction.on_commit(
            lambda: EmailService.enqueue(
                template="two_factor_disabled",
                recipient=user.email,
                subject=f"Two-factor authentication disabled on {settings.SITE_NAME}",
                context={"user": user},
            )
        )


class AuthenticationService:
    @staticmethod
    def login(
        *, request, identifier: str, password: str, code: str = "", remember_me: bool = False
    ) -> tuple[User, UserSession]:
        ip = get_client_ip(request)
        lock_state = LoginProtectionService.check(identifier, ip)
        if lock_state.locked:
            raise APIException(
                "Too many attempts. Try again later.",
                code="ACCOUNT_LOCKED",
                status_code=429,
                fields={"retry_after": lock_state.retry_after},
            )
        user = authenticate(request=request, username=identifier, password=password)
        if user is None:
            new_state = LoginProtectionService.register_failure(identifier, ip)
            SecurityEventService.record(
                SecurityEventType.LOGIN_FAILED,
                request=request,
                metadata={"identifier_hash": LoginProtectionService._digest(identifier)},
            )
            code_name = "ACCOUNT_LOCKED" if new_state.locked else "AUTHENTICATION_FAILED"
            if new_state.account_locked:
                LoginProtectionService.lock_known_account(
                    identifier=identifier,
                    retry_after=new_state.retry_after,
                    request=request,
                )
            raise APIException(
                "Invalid credentials.", code=code_name, status_code=429 if new_state.locked else 401
            )
        security_settings, _ = UserSecuritySettings.objects.get_or_create(user=user)
        if security_settings.is_locked:
            retry_after = max(
                1, int((security_settings.locked_until - timezone.now()).total_seconds())
            )
            raise APIException(
                "Too many attempts. Try again later.",
                code="ACCOUNT_LOCKED",
                status_code=429,
                fields={"retry_after": retry_after},
            )
        if security_settings.locked_until:
            security_settings.locked_until = None
            security_settings.save(update_fields=["locked_until", "updated_at"])
            SecurityEventService.record(
                SecurityEventType.ACCOUNT_UNLOCKED,
                user=user,
                request=request,
            )
        if (
            user.status == AccountStatus.BANNED
            or user.bans.filter(revoked_at__isnull=True, starts_at__lte=timezone.now())
            .filter(Q(expires_at__isnull=True) | Q(expires_at__gt=timezone.now()))
            .exists()
        ):
            raise APIException(
                "This account is unavailable.", code="ACCOUNT_BANNED", status_code=403
            )
        if user.status != AccountStatus.ACTIVE:
            raise APIException(
                "This account is unavailable.", code="AUTHENTICATION_FAILED", status_code=403
            )
        try:
            two_factor_enabled = settings.ENABLE_TWO_FACTOR and user.two_factor.is_enabled
        except TwoFactorCredential.DoesNotExist:
            two_factor_enabled = False
        if two_factor_enabled:
            if not code:
                raise APIException(
                    "A two-factor code is required.", code="TWO_FACTOR_REQUIRED", status_code=401
                )
            valid, _ = TwoFactorService.verify(user=user, code=code)
            if not valid:
                LoginProtectionService.register_failure(identifier, ip)
                raise APIException(
                    "Invalid credentials.", code="AUTHENTICATION_FAILED", status_code=401
                )
        LoginProtectionService.reset(identifier, ip)
        login(request, user)
        request.session.set_expiry(60 * 60 * 24 * 30 if remember_me else 0)
        user_session, is_new_device = SessionService.register(user=user, request=request)
        user.last_login_ip = ip
        user.last_login = timezone.now()
        user.save(update_fields=["last_login_ip", "last_login", "updated_at"])
        SecurityEventService.record(SecurityEventType.LOGIN_SUCCESS, user=user, request=request)
        if is_new_device:
            SecurityEventService.record(
                SecurityEventType.NEW_DEVICE_LOGIN, user=user, request=request
            )
            preferences, _ = UserPreferences.objects.get_or_create(user=user)
            security_settings, _ = UserSecuritySettings.objects.get_or_create(user=user)
            if preferences.security_emails and security_settings.notify_new_device:
                transaction.on_commit(
                    lambda: EmailService.enqueue(
                        template="new_device_login",
                        recipient=user.email,
                        subject=f"New sign-in to {settings.SITE_NAME}",
                        context={"user": user, "session": user_session},
                    )
                )
        return user, user_session


class AccountService:
    @staticmethod
    @transaction.atomic
    def register_user(
        *,
        email: str,
        username: str,
        password: str,
        first_name: str = "",
        last_name: str = "",
        request=None,
    ) -> User:
        validate_password(password)
        try:
            user = User.objects.create_user(
                email=email,
                username=username,
                password=password,
                first_name=first_name,
                last_name=last_name,
            )
        except IntegrityError as exc:
            raise APIException(
                "An account with those details already exists.", code="CONFLICT", status_code=409
            ) from exc
        UserProfile.objects.create(user=user)
        UserPreferences.objects.create(user=user)
        UserSecuritySettings.objects.create(user=user)
        default_role = Role.objects.filter(slug="user").first()
        if default_role:
            UserRole.objects.get_or_create(user=user, role=default_role)
        raw_token = TokenService.issue(
            user=user,
            purpose=TokenPurpose.EMAIL_VERIFICATION,
            ttl=timedelta(hours=24),
        )
        AuditService.record(
            action="user.created",
            target=user,
            actor=user,
            request=request,
            after={"status": user.status},
        )
        transaction.on_commit(
            lambda: EmailService.enqueue(
                template="email_verification",
                recipient=user.email,
                subject=f"Verify your {settings.SITE_NAME} email",
                context={
                    "user": user,
                    "verification_url": f"{settings.SITE_URL}/verify-email?token={raw_token}",
                },
            )
        )
        return user

    @staticmethod
    @transaction.atomic
    def verify_email(*, raw_token: str, request=None) -> User:
        token = TokenService.consume(raw_token=raw_token, purpose=TokenPurpose.EMAIL_VERIFICATION)
        user = User.objects.select_for_update().get(pk=token.user_id)
        if not user.email_verified_at:
            user.email_verified_at = timezone.now()
            if user.status == AccountStatus.PENDING:
                user.status = AccountStatus.ACTIVE
            user.save(update_fields=["email_verified_at", "status", "updated_at"])
            AuditService.record(action="email.verified", target=user, actor=user, request=request)
            transaction.on_commit(
                lambda: EmailService.enqueue(
                    template="welcome",
                    recipient=user.email,
                    subject=f"Welcome to {settings.SITE_NAME}",
                    context={"user": user},
                )
            )
        return user

    @staticmethod
    def resend_verification(*, email: str) -> None:
        user = User.objects.filter(
            email__iexact=email.strip(), email_verified_at__isnull=True, is_active=True
        ).first()
        if not user:
            return
        raw = TokenService.issue(
            user=user, purpose=TokenPurpose.EMAIL_VERIFICATION, ttl=timedelta(hours=24)
        )
        EmailService.enqueue(
            template="email_verification",
            recipient=user.email,
            subject=f"Verify your {settings.SITE_NAME} email",
            context={
                "user": user,
                "verification_url": f"{settings.SITE_URL}/verify-email?token={raw}",
            },
        )

    @staticmethod
    def request_password_reset(*, email: str) -> None:
        user = User.objects.filter(email__iexact=email.strip(), is_active=True).first()
        if not user:
            return
        raw = TokenService.issue(
            user=user,
            purpose=TokenPurpose.PASSWORD_RESET,
            ttl=timedelta(seconds=settings.PASSWORD_RESET_TIMEOUT),
        )
        EmailService.enqueue(
            template="password_reset",
            recipient=user.email,
            subject=f"Reset your {settings.SITE_NAME} password",
            context={"user": user, "reset_url": f"{settings.SITE_URL}/reset-password?token={raw}"},
        )

    @staticmethod
    @transaction.atomic
    def reset_password(*, raw_token: str, new_password: str, request=None) -> User:
        token = TokenService.consume(raw_token=raw_token, purpose=TokenPurpose.PASSWORD_RESET)
        user = User.objects.select_for_update().get(pk=token.user_id)
        validate_password(new_password, user=user)
        user.set_password(new_password)
        user.save(update_fields=["password", "updated_at"])
        settings_row, _ = UserSecuritySettings.objects.get_or_create(user=user)
        settings_row.password_changed_at = timezone.now()
        settings_row.save(update_fields=["password_changed_at", "updated_at"])
        SessionService.revoke_all(user=user, actor=user, request=request)
        TokenService.revoke_all_jwt(user=user)
        SecurityEventService.record(SecurityEventType.PASSWORD_RESET, user=user, request=request)
        AuditService.record(action="password.reset", target=user, actor=user, request=request)
        transaction.on_commit(
            lambda: EmailService.enqueue(
                template="password_changed",
                recipient=user.email,
                subject=f"Your {settings.SITE_NAME} password was changed",
                context={"user": user},
            )
        )
        return user

    @staticmethod
    @transaction.atomic
    def change_password(*, user: User, old_password: str, new_password: str, request=None) -> None:
        locked = User.objects.select_for_update().get(pk=user.pk)
        if not locked.check_password(old_password):
            raise APIException(
                "Authentication failed.", code="AUTHENTICATION_FAILED", status_code=401
            )
        validate_password(new_password, user=locked)
        locked.set_password(new_password)
        locked.save(update_fields=["password", "updated_at"])
        security_settings, _ = UserSecuritySettings.objects.get_or_create(user=locked)
        security_settings.password_changed_at = timezone.now()
        security_settings.save(update_fields=["password_changed_at", "updated_at"])
        SessionService.revoke_all(user=locked, actor=locked, request=request, exclude_current=True)
        TokenService.revoke_all_jwt(user=locked)
        SecurityEventService.record(
            SecurityEventType.PASSWORD_CHANGED, user=locked, request=request
        )
        AuditService.record(action="password.changed", target=locked, actor=locked, request=request)
        transaction.on_commit(
            lambda: EmailService.enqueue(
                template="password_changed",
                recipient=locked.email,
                subject=f"Your {settings.SITE_NAME} password was changed",
                context={"user": locked},
            )
        )

    @staticmethod
    def request_email_change(*, user: User, password: str, new_email: str) -> None:
        normalized = User.objects.normalize_email_address(new_email)
        if not user.check_password(password):
            raise APIException(
                "Authentication failed.", code="AUTHENTICATION_FAILED", status_code=401
            )
        if User.objects.filter(email__iexact=normalized).exclude(pk=user.pk).exists():
            raise APIException(
                "That email address is unavailable.", code="CONFLICT", status_code=409
            )
        raw = TokenService.issue(
            user=user,
            purpose=TokenPurpose.EMAIL_CHANGE,
            ttl=timedelta(hours=1),
            metadata={"new_email": normalized},
        )
        EmailService.enqueue(
            template="email_verification",
            recipient=normalized,
            subject=f"Confirm your new {settings.SITE_NAME} email",
            context={
                "user": user,
                "verification_url": f"{settings.SITE_URL}/confirm-email-change?token={raw}",
            },
        )

    @staticmethod
    @transaction.atomic
    def confirm_email_change(*, raw_token: str, request=None) -> User:
        token = TokenService.consume(raw_token=raw_token, purpose=TokenPurpose.EMAIL_CHANGE)
        user = User.objects.select_for_update().get(pk=token.user_id)
        old_email = user.email
        new_email = token.metadata["new_email"]
        if User.objects.filter(email__iexact=new_email).exclude(pk=user.pk).exists():
            raise APIException(
                "That email address is unavailable.", code="CONFLICT", status_code=409
            )
        user.email = new_email
        user.email_verified_at = timezone.now()
        user.save(update_fields=["email", "email_verified_at", "updated_at"])
        SessionService.revoke_all(user=user, actor=user, request=request, exclude_current=True)
        TokenService.revoke_all_jwt(user=user)
        SecurityEventService.record(SecurityEventType.EMAIL_CHANGED, user=user, request=request)
        AuditService.record(
            action="email.changed",
            target=user,
            actor=user,
            request=request,
            before={"email": old_email},
            after={"email": new_email},
        )
        transaction.on_commit(
            lambda: EmailService.enqueue(
                template="email_changed",
                recipient=old_email,
                subject=f"Your {settings.SITE_NAME} email was changed",
                context={"user": user, "new_email": new_email},
            )
        )
        return user

    @staticmethod
    @transaction.atomic
    def change_username(*, user: User, username: str, request=None) -> User:
        locked = User.objects.select_for_update().get(pk=user.pk)
        old = locked.username
        locked.username = username.strip()
        try:
            locked.full_clean(exclude={"password"}, validate_unique=False)
            locked.save(update_fields=["username", "updated_at"])
        except IntegrityError as exc:
            raise APIException(
                "That username is unavailable.", code="CONFLICT", status_code=409
            ) from exc
        AuditService.record(
            action="username.changed",
            target=locked,
            actor=locked,
            request=request,
            before={"username": old},
            after={"username": locked.username},
        )
        return locked

    @staticmethod
    @transaction.atomic
    def deactivate(*, user: User, password: str, request=None) -> None:
        locked = User.objects.select_for_update().get(pk=user.pk)
        if not locked.check_password(password):
            raise APIException(
                "Authentication failed.", code="AUTHENTICATION_FAILED", status_code=401
            )
        locked.status = AccountStatus.DEACTIVATED
        locked.is_active = False
        locked.save(update_fields=["status", "is_active", "updated_at"])
        SessionService.revoke_all(user=locked, actor=locked, request=request)
        TokenService.revoke_all_jwt(user=locked)
        SecurityEventService.record(
            SecurityEventType.ACCOUNT_DEACTIVATED, user=locked, request=request
        )
        AuditService.record(
            action="account.deactivated", target=locked, actor=locked, request=request
        )

    @staticmethod
    def request_deletion(*, user: User, password: str) -> None:
        if not user.check_password(password):
            raise APIException(
                "Authentication failed.", code="AUTHENTICATION_FAILED", status_code=401
            )
        raw = TokenService.issue(
            user=user, purpose=TokenPurpose.ACCOUNT_DELETION, ttl=timedelta(hours=1)
        )
        EmailService.enqueue(
            template="account_security_warning",
            recipient=user.email,
            subject=f"Confirm deletion of your {settings.SITE_NAME} account",
            context={"user": user, "action_url": f"{settings.SITE_URL}/delete-account?token={raw}"},
        )

    @staticmethod
    @transaction.atomic
    def confirm_deletion(*, raw_token: str, request=None) -> None:
        token = TokenService.consume(raw_token=raw_token, purpose=TokenPurpose.ACCOUNT_DELETION)
        user = User.objects.select_for_update().get(pk=token.user_id)
        original = {"email": user.email, "username": user.username}
        suffix = user.pk.hex
        avatar_name = user.avatar.name
        avatar_storage = user.avatar.storage
        user.email = f"deleted-{suffix}@invalid.local"
        user.username = f"deleted-{suffix}"
        user.first_name = ""
        user.last_name = ""
        user.phone = ""
        user.avatar = ""
        user.status = AccountStatus.DELETED
        user.is_active = False
        user.email_verified_at = None
        user.phone_verified_at = None
        user.set_unusable_password()
        user.save()
        UserProfile.objects.filter(user=user).update(bio="", website="", location="")
        SessionService.revoke_all(user=user, actor=user, request=request)
        TokenService.revoke_all_jwt(user=user)
        SecurityEventService.record(SecurityEventType.ACCOUNT_DELETED, user=user, request=request)
        AuditService.record(
            action="account.deleted",
            target=user,
            actor=user,
            request=request,
            before=original,
            after={"status": AccountStatus.DELETED},
            target_repr=f"Deleted user {suffix}",
        )
        if avatar_name:
            transaction.on_commit(lambda: avatar_storage.delete(avatar_name))
        transaction.on_commit(
            lambda: EventBus.publish(
                ApplicationEvent(
                    name="account.deleted",
                    actor_id=str(user.pk),
                    target_type="accounts.user",
                    target_id=str(user.pk),
                )
            )
        )
