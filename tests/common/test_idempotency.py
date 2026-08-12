import pytest
from django.urls import reverse

from apps.api_keys.models import APIKey

pytestmark = pytest.mark.django_db


def test_idempotency_replays_same_response(authenticated_client):
    headers = {"HTTP_IDEMPOTENCY_KEY": "stable-create-key"}
    first = authenticated_client.post(
        reverse("api-key-list"),
        {"name": "CLI", "scopes": []},
        format="json",
        **headers,
    )
    second = authenticated_client.post(
        reverse("api-key-list"),
        {"name": "CLI", "scopes": []},
        format="json",
        **headers,
    )

    assert first.status_code == second.status_code == 201
    assert first.data == second.data
    assert second.headers["Idempotent-Replayed"] == "true"
    assert APIKey.objects.count() == 1


def test_idempotency_rejects_key_reuse_for_different_body(authenticated_client):
    headers = {"HTTP_IDEMPOTENCY_KEY": "conflicting-key"}
    authenticated_client.post(
        reverse("api-key-list"), {"name": "One", "scopes": []}, format="json", **headers
    )

    response = authenticated_client.post(
        reverse("api-key-list"), {"name": "Two", "scopes": []}, format="json", **headers
    )

    assert response.status_code == 409
    assert response.data["error"]["code"] == "CONFLICT"
