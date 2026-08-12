from __future__ import annotations

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

from common.models import TimeStampedModel, UUIDModel


class Permission(UUIDModel, TimeStampedModel):
    codename = models.CharField(max_length=150, unique=True)
    description = models.CharField(max_length=255, blank=True)
    is_system = models.BooleanField(default=False)

    class Meta:
        ordering = ["codename"]

    def clean(self):
        if self.codename.count(".") != 1 or any(
            not part.replace("_", "").isalnum() for part in self.codename.split(".")
        ):
            raise ValidationError({"codename": "Use the 'resource.action' format."})

    def __str__(self) -> str:
        return self.codename

    def delete(self, *args, **kwargs):
        if self.is_system:
            raise ValidationError("System permissions cannot be deleted.")
        return super().delete(*args, **kwargs)


class Role(UUIDModel, TimeStampedModel):
    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    priority = models.PositiveSmallIntegerField(default=0, db_index=True)
    is_system = models.BooleanField(default=False)
    permissions = models.ManyToManyField(Permission, through="RolePermission", related_name="roles")

    class Meta:
        ordering = ["-priority", "name"]

    def delete(self, *args, **kwargs):
        if self.is_system:
            raise ValidationError("System roles cannot be deleted.")
        return super().delete(*args, **kwargs)

    def __str__(self) -> str:
        return self.name


class RolePermission(UUIDModel):
    role = models.ForeignKey(Role, on_delete=models.CASCADE, related_name="permission_links")
    permission = models.ForeignKey(Permission, on_delete=models.CASCADE, related_name="role_links")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["role", "permission"], name="authz_role_permission_unique"
            )
        ]


class UserRole(UUIDModel):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="role_assignments"
    )
    role = models.ForeignKey(Role, on_delete=models.PROTECT, related_name="user_assignments")
    granted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="granted_role_assignments",
    )
    valid_from = models.DateTimeField(default=timezone.now)
    valid_until = models.DateTimeField(null=True, blank=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["user", "role"], name="authz_user_role_unique")
        ]
        indexes = [
            models.Index(
                fields=["user", "valid_from", "valid_until"], name="authz_user_role_valid_idx"
            )
        ]

    @property
    def is_valid(self) -> bool:
        now = timezone.now()
        return self.valid_from <= now and (self.valid_until is None or self.valid_until > now)


class OverrideEffect(models.TextChoices):
    ALLOW = "allow", "Allow"
    DENY = "deny", "Deny"


class UserPermissionOverride(UUIDModel, TimeStampedModel):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="permission_overrides"
    )
    permission = models.ForeignKey(
        Permission, on_delete=models.CASCADE, related_name="user_overrides"
    )
    effect = models.CharField(max_length=8, choices=OverrideEffect.choices)
    reason = models.CharField(max_length=255, blank=True)
    granted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="granted_permission_overrides",
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user", "permission"], name="authz_user_permission_unique"
            )
        ]
        indexes = [models.Index(fields=["user", "effect"], name="authz_user_override_idx")]
