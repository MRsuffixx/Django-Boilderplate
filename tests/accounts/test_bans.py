from datetime import timedelta

import pytest
from django.utils import timezone

from apps.accounts.models import AccountStatus
from apps.accounts.services import BanService
from apps.api_keys.services import APIKeyService
from apps.authorization.models import RolePermission, UserRole
from apps.authorization.services import PermissionService
from tests.factories import PermissionFactory, RoleFactory

pytestmark = pytest.mark.django_db


def test_temporary_ban_changes_account_state_and_can_be_revoked(user):
    ban = BanService.ban(
        user=user,
        reason="Security review",
        expires_at=timezone.now() + timedelta(hours=1),
    )
    user.refresh_from_db()
    assert user.status == AccountStatus.BANNED
    assert ban.is_active

    BanService.revoke(ban=ban)
    user.refresh_from_db()
    assert user.status == AccountStatus.ACTIVE


def test_permanent_ban_has_no_expiry(user):
    ban = BanService.ban(user=user, reason="Policy violation")
    assert ban.expires_at is None
    assert ban.is_active


def test_active_ban_blocks_permissions_and_api_keys_even_if_status_is_stale(user):
    permission = PermissionFactory(codename="documents.view")
    role = RoleFactory()
    RolePermission.objects.create(role=role, permission=permission)
    UserRole.objects.create(user=user, role=role)
    _, raw = APIKeyService.create(owner=user, name="Integration", scopes=[])
    ban = user.bans.create(
        reason="Scheduled",
        starts_at=timezone.now() - timedelta(minutes=1),
        expires_at=timezone.now() + timedelta(hours=1),
    )
    assert ban.is_active

    assert not PermissionService.has_permission(user, "documents.view")
    assert APIKeyService.authenticate(raw) is None
