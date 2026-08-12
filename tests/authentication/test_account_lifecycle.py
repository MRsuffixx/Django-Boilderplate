from datetime import timedelta

import pytest
from django.core import mail
from django.test import RequestFactory

from apps.accounts.models import AccountStatus, UserProfile
from apps.authentication.models import TokenPurpose
from apps.authentication.services import AccountService, TokenService
from apps.security.models import SecurityEventType

pytestmark = pytest.mark.django_db

PASSWORD = "A-very-secure-test-password-42"


def test_change_password_revokes_credentials_and_records_event(user):
    AccountService.change_password(
        user=user,
        old_password=PASSWORD,
        new_password="Another-very-secure-password-43",
        request=RequestFactory().post("/"),
    )

    user.refresh_from_db()
    assert user.check_password("Another-very-secure-password-43")
    assert user.security_events.filter(event_type=SecurityEventType.PASSWORD_CHANGED).exists()


def test_email_change_requires_confirmation_of_new_address(user):
    AccountService.request_email_change(
        user=user,
        password=PASSWORD,
        new_email="changed@example.test",
    )
    token_row = user.one_time_tokens.get(purpose=TokenPurpose.EMAIL_CHANGE)
    assert token_row.metadata["new_email"] == "changed@example.test"
    assert mail.outbox[-1].to == ["changed@example.test"]

    # The raw token is intentionally available only in the outbound message.
    raw = mail.outbox[-1].body.split("token=", 1)[1].split()[0]
    AccountService.confirm_email_change(raw_token=raw)

    user.refresh_from_db()
    assert user.email == "changed@example.test"
    assert user.is_email_verified


def test_confirmed_deletion_pseudonymizes_identity_and_profile(user):
    UserProfile.objects.create(user=user, bio="Personal biography", location="Personal location")
    raw = TokenService.issue(
        user=user,
        purpose=TokenPurpose.ACCOUNT_DELETION,
        ttl=timedelta(hours=1),
    )

    AccountService.confirm_deletion(raw_token=raw)

    user.refresh_from_db()
    user.profile.refresh_from_db()
    assert user.status == AccountStatus.DELETED
    assert not user.is_active
    assert not user.has_usable_password()
    assert user.email.endswith("@invalid.local")
    assert user.profile.bio == ""
    assert user.security_events.filter(event_type=SecurityEventType.ACCOUNT_DELETED).exists()
