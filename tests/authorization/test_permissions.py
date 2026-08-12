from datetime import timedelta

import pytest
from django.utils import timezone

from apps.authorization.models import (
    OverrideEffect,
    RolePermission,
    UserPermissionOverride,
    UserRole,
)
from apps.authorization.services import PermissionService
from tests.factories import PermissionFactory, RoleFactory

pytestmark = pytest.mark.django_db


def test_active_role_grants_permission(user):
    permission = PermissionFactory(codename="documents.view")
    role = RoleFactory()
    RolePermission.objects.create(role=role, permission=permission)
    UserRole.objects.create(user=user, role=role)

    assert PermissionService.has_permission(user, "documents.view")


def test_expired_role_does_not_grant_permission(user):
    permission = PermissionFactory(codename="documents.view")
    role = RoleFactory()
    RolePermission.objects.create(role=role, permission=permission)
    UserRole.objects.create(
        user=user,
        role=role,
        valid_from=timezone.now() - timedelta(days=2),
        valid_until=timezone.now() - timedelta(days=1),
    )

    assert not PermissionService.has_permission(user, "documents.view")


def test_explicit_deny_overrides_role_and_superuser(user):
    permission = PermissionFactory(codename="documents.delete")
    role = RoleFactory()
    RolePermission.objects.create(role=role, permission=permission)
    UserRole.objects.create(user=user, role=role)
    user.is_superuser = True
    user.save(update_fields=["is_superuser"])
    UserPermissionOverride.objects.create(
        user=user,
        permission=permission,
        effect=OverrideEffect.DENY,
    )

    assert not PermissionService.has_permission(user, "documents.delete")


def test_explicit_allow_grants_without_role(user):
    permission = PermissionFactory(codename="documents.export")
    UserPermissionOverride.objects.create(
        user=user,
        permission=permission,
        effect=OverrideEffect.ALLOW,
    )

    assert PermissionService.has_permission(user, "documents.export")
