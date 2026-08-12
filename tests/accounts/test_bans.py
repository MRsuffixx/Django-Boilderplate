from datetime import timedelta

import pytest
from django.utils import timezone

from apps.accounts.models import AccountStatus
from apps.accounts.services import BanService

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
