from __future__ import annotations

import re

import pytest
from django.core import mail
from django.urls import reverse

from apps.accounts.models import AccountStatus, User
from apps.audit.models import AuditLog
from apps.authentication.models import TokenPurpose
from apps.security.models import SecurityEvent, SecurityEventType


pytestmark = pytest.mark.django_db

PASSWORD = "A-very-secure-test-password-42"


def _token_from_body(body: str) -> str:
    match = re.search(r"token=([^\s<]+)", body)
    assert match
    return match.group(1)


def test_registration_creates_related_state_and_sends_verification(api_client):
    response = api_client.post(
        reverse("register"),
        {
            "email": "New@Example.Test",
            "username": "new-user",
            "password": PASSWORD,
            "first_name": "New",
        },
        format="json",
    )

    assert response.status_code == 201
    assert response.data["success"] is True
    user = User.objects.get(email="new@example.test")
    assert user.status == AccountStatus.PENDING
    assert user.profile
    assert user.preferences
    assert user.security_settings
    assert user.one_time_tokens.filter(purpose=TokenPurpose.EMAIL_VERIFICATION).exists()
    assert len(mail.outbox) == 1
    assert AuditLog.objects.filter(action="user.created", target_id=str(user.pk)).exists()


def test_email_verification_activates_pending_user(api_client):
    api_client.post(
        reverse("register"),
        {"email": "new@example.test", "username": "new-user", "password": PASSWORD},
        format="json",
    )
    token = _token_from_body(mail.outbox[0].body)

    response = api_client.post(reverse("verify-email"), {"token": token}, format="json")

    user = User.objects.get(email="new@example.test")
    assert response.status_code == 200
    assert user.status == AccountStatus.ACTIVE
    assert user.is_email_verified


def test_verification_token_cannot_be_reused(api_client):
    api_client.post(
        reverse("register"),
        {"email": "new@example.test", "username": "new-user", "password": PASSWORD},
        format="json",
    )
    token = _token_from_body(mail.outbox[0].body)
    api_client.post(reverse("verify-email"), {"token": token}, format="json")

    response = api_client.post(reverse("verify-email"), {"token": token}, format="json")

    assert response.status_code == 400
    assert response.data["error"]["code"] == "INVALID_TOKEN"


def test_login_accepts_email_or_username_and_returns_rotatable_tokens(api_client, user):
    response = api_client.post(
        reverse("login"),
        {"identifier": user.username, "password": PASSWORD, "remember_me": True},
        format="json",
        HTTP_USER_AGENT="Test Browser",
    )

    assert response.status_code == 200
    assert response.data["data"]["access"]
    assert response.data["data"]["refresh"]
    assert user.user_sessions.count() == 1
    assert SecurityEvent.objects.filter(user=user, event_type=SecurityEventType.LOGIN_SUCCESS).exists()


def test_login_error_does_not_reveal_unknown_account(api_client, user):
    known = api_client.post(
        reverse("login"),
        {"identifier": user.email, "password": "wrong"},
        format="json",
    )
    unknown = api_client.post(
        reverse("login"),
        {"identifier": "unknown@example.test", "password": "wrong"},
        format="json",
    )

    assert known.status_code == unknown.status_code == 401
    assert known.data["error"]["message"] == unknown.data["error"]["message"]


def test_password_reset_is_enumeration_safe_and_revokes_sessions(api_client, user):
    response = api_client.post(reverse("password-reset"), {"email": user.email}, format="json")
    unknown = api_client.post(
        reverse("password-reset"),
        {"email": "unknown@example.test"},
        format="json",
    )

    assert response.status_code == unknown.status_code == 200
    assert response.data == unknown.data
    token = _token_from_body(mail.outbox[0].body)
    confirm = api_client.post(
        reverse("password-reset-confirm"),
        {"token": token, "new_password": "Another-very-secure-password-43"},
        format="json",
    )
    assert confirm.status_code == 200
    user.refresh_from_db()
    assert user.check_password("Another-very-secure-password-43")


def test_logout_blacklists_refresh_token(api_client, user):
    login_response = api_client.post(
        reverse("login"),
        {"identifier": user.email, "password": PASSWORD},
        format="json",
    )
    refresh = login_response.data["data"]["refresh"]
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {login_response.data['data']['access']}")

    response = api_client.post(reverse("logout"), {"refresh": refresh}, format="json")
    refresh_response = api_client.post(reverse("token-refresh"), {"refresh": refresh}, format="json")

    assert response.status_code == 200
    assert refresh_response.status_code == 401
