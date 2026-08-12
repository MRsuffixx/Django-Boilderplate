import pytest
from django.test import RequestFactory
from django.urls import reverse

from apps.api_keys.services import APIKeyService


pytestmark = pytest.mark.django_db


def test_api_key_is_only_stored_as_hash(user):
    api_key, raw = APIKeyService.create(
        owner=user,
        name="Integration",
        scopes=["profile.read"],
    )

    assert raw.startswith(f"dk_{api_key.prefix}.")
    assert raw != api_key.key_hash
    assert raw not in api_key.key_hash
    assert APIKeyService.authenticate(raw) == api_key


def test_api_key_creation_returns_raw_key_once(authenticated_client):
    response = authenticated_client.post(
        reverse("api-key-list"),
        {"name": "CLI", "scopes": ["profile.read"]},
        format="json",
        HTTP_IDEMPOTENCY_KEY="create-key-1",
    )

    assert response.status_code == 201
    assert response.data["data"]["key"].startswith("dk_")
    detail = authenticated_client.get(
        reverse("api-key-detail", kwargs={"pk": response.data["data"]["id"]})
    )
    assert "key" not in detail.data["data"]


def test_revoked_api_key_cannot_authenticate(user):
    api_key, raw = APIKeyService.create(owner=user, name="Integration", scopes=[])
    APIKeyService.revoke(api_key=api_key)

    assert APIKeyService.authenticate(raw) is None
