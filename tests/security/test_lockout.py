import pytest
from django.urls import reverse

from apps.security.models import LoginThrottleState, SecurityEventType

pytestmark = pytest.mark.django_db


def test_repeated_failures_create_temporary_account_lock(api_client, user, settings):
    settings.LOGIN_MAX_ATTEMPTS = 2
    settings.LOGIN_LOCKOUT_SECONDS = 60
    payload = {"identifier": user.email, "password": "wrong"}

    first = api_client.post(reverse("login"), payload, format="json")
    second = api_client.post(reverse("login"), payload, format="json")

    user.security_settings.refresh_from_db()
    assert first.status_code == 401
    assert second.status_code == 429
    assert user.security_settings.is_locked
    assert user.security_events.filter(event_type=SecurityEventType.ACCOUNT_LOCKED).exists()
    assert LoginThrottleState.objects.count() == 3
