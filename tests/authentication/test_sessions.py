import pytest
from django.contrib.sessions.backends.db import SessionStore
from django.test import RequestFactory
from django.urls import reverse

from apps.authentication.services import SessionService


pytestmark = pytest.mark.django_db


def _request_for(user):
    request = RequestFactory().get("/", HTTP_USER_AGENT="Mozilla/5.0")
    request.user = user
    request.session = SessionStore()
    request.session.create()
    request.request_id = "test-request"
    return request


def test_session_store_does_not_keep_plain_session_key(user):
    request = _request_for(user)
    session_key = request.session.session_key

    user_session, _ = SessionService.register(user=user, request=request)

    assert user_session.session_key_hash != session_key
    assert session_key not in user_session.encrypted_session_key


def test_user_can_only_revoke_own_session(authenticated_client, user):
    request = _request_for(user)
    user_session, _ = SessionService.register(user=user, request=request)

    response = authenticated_client.post(
        reverse("user-session-revoke", kwargs={"identifier": user_session.identifier}),
        format="json",
    )

    assert response.status_code == 200
    user_session.refresh_from_db()
    assert user_session.is_revoked
