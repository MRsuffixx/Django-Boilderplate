from __future__ import annotations

import uuid

from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.contrib.auth.models import PermissionsMixin
from django.core.validators import RegexValidator
from django.db import models
from django.db.models.functions import Lower
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from common.models import TimeStampedModel, UUIDModel


def avatar_upload_to(instance: "User", filename: str) -> str:
    extension = filename.rsplit(".", 1)[-1].lower() if "." in filename else "bin"
    return f"avatars/{instance.pk}/{uuid.uuid4().hex}.{extension}"


class AccountStatus(models.TextChoices):
    ACTIVE = "active", _("Active")
    PENDING = "pending", _("Pending")
    SUSPENDED = "suspended", _("Suspended")
    BANNED = "banned", _("Banned")
    DEACTIVATED = "deactivated", _("Deactivated")
    DELETED = "deleted", _("Deleted")


class UserManager(BaseUserManager["User"]):
    use_in_migrations = True

    @staticmethod
    def normalize_email_address(email: str) -> str:
        return BaseUserManager.normalize_email(email.strip()).casefold()

    def _create_user(self, email: str, username: str, password: str | None, **extra_fields):
        if not email:
            raise ValueError("Email is required")
        if not username:
            raise ValueError("Username is required")
        user = self.model(
            email=self.normalize_email_address(email),
            username=username.strip(),
            **extra_fields,
        )
        user.set_password(password)
        user.full_clean(exclude={"password"}, validate_unique=False, validate_constraints=False)
        user.save(using=self._db)
        return user

    def create_user(self, email: str, username: str, password: str | None = None, **extra_fields):
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        extra_fields.setdefault("status", AccountStatus.PENDING)
        return self._create_user(email, username, password, **extra_fields)

    def create_superuser(self, email: str, username: str, password: str | None = None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)
        extra_fields.setdefault("status", AccountStatus.ACTIVE)
        extra_fields.setdefault("email_verified_at", timezone.now())
        if not extra_fields["is_staff"] or not extra_fields["is_superuser"]:
            raise ValueError("Superusers must have is_staff=True and is_superuser=True")
        return self._create_user(email, username, password, **extra_fields)


class User(UUIDModel, AbstractBaseUser, PermissionsMixin):
    email = models.EmailField(_("email address"), max_length=254, unique=True)
    username = models.CharField(
        _("username"),
        max_length=150,
        unique=True,
        validators=[RegexValidator(r"^[\w.@+-]+$", _("Use letters, numbers, and @/./+/-/_ only."))],
    )
    first_name = models.CharField(_("first name"), max_length=150, blank=True)
    last_name = models.CharField(_("last name"), max_length=150, blank=True)
    avatar = models.ImageField(upload_to=avatar_upload_to, blank=True)
    phone = models.CharField(max_length=32, blank=True)
    status = models.CharField(max_length=24, choices=AccountStatus.choices, default=AccountStatus.PENDING, db_index=True)
    email_verified_at = models.DateTimeField(null=True, blank=True)
    phone_verified_at = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(default=timezone.now)
    last_login_ip = models.GenericIPAddressField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["username"]

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(Lower("email"), name="accounts_user_email_ci_unique"),
            models.UniqueConstraint(Lower("username"), name="accounts_user_username_ci_unique"),
        ]
        indexes = [models.Index(fields=["status", "created_at"], name="acct_user_status_created_idx")]

    def save(self, *args, **kwargs):
        self.email = UserManager.normalize_email_address(self.email)
        self.username = self.username.strip()
        super().save(*args, **kwargs)

    @property
    def is_email_verified(self) -> bool:
        return self.email_verified_at is not None

    @property
    def is_phone_verified(self) -> bool:
        return self.phone_verified_at is not None

    @property
    def display_name(self) -> str:
        return self.get_full_name() or self.username

    def get_full_name(self) -> str:
        return f"{self.first_name} {self.last_name}".strip()

    def get_short_name(self) -> str:
        return self.first_name or self.username

    def __str__(self) -> str:
        return self.email


class UserProfile(UUIDModel, TimeStampedModel):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    bio = models.TextField(blank=True, max_length=2000)
    website = models.URLField(blank=True)
    location = models.CharField(max_length=255, blank=True)

    def __str__(self) -> str:
        return f"Profile: {self.user}"


class UserPreferences(UUIDModel, TimeStampedModel):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="preferences")
    language = models.CharField(max_length=10, default="en")
    timezone = models.CharField(max_length=64, default="UTC")
    email_notifications = models.BooleanField(default=True)
    security_emails = models.BooleanField(default=True)

    def __str__(self) -> str:
        return f"Preferences: {self.user}"


class UserSecuritySettings(UUIDModel, TimeStampedModel):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="security_settings")
    password_changed_at = models.DateTimeField(null=True, blank=True)
    locked_until = models.DateTimeField(null=True, blank=True, db_index=True)
    notify_new_device = models.BooleanField(default=True)

    @property
    def is_locked(self) -> bool:
        return bool(self.locked_until and self.locked_until > timezone.now())

    def __str__(self) -> str:
        return f"Security settings: {self.user}"


class UserBan(UUIDModel):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="bans")
    reason = models.TextField()
    banned_by = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL, related_name="issued_bans"
    )
    starts_at = models.DateTimeField(default=timezone.now)
    expires_at = models.DateTimeField(null=True, blank=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    revoked_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["user", "revoked_at", "expires_at"], name="acct_ban_active_idx")]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(expires_at__isnull=True) | models.Q(expires_at__gt=models.F("starts_at")),
                name="acct_ban_expiry_after_start",
            )
        ]

    @property
    def is_active(self) -> bool:
        now = timezone.now()
        return self.revoked_at is None and self.starts_at <= now and (self.expires_at is None or self.expires_at > now)

    def __str__(self) -> str:
        return f"Ban for {self.user}"
