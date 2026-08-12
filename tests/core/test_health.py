import pytest
from django.urls import reverse

pytestmark = pytest.mark.django_db


def test_liveness_is_public_and_has_request_id(api_client):
    response = api_client.get(reverse("health-live"), HTTP_X_REQUEST_ID="valid-request-123")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    assert response.headers["X-Request-ID"] == "valid-request-123"


def test_invalid_incoming_request_id_is_replaced(api_client):
    response = api_client.get(reverse("health-live"), HTTP_X_REQUEST_ID="invalid id with spaces")

    assert response.headers["X-Request-ID"] != "invalid id with spaces"


def test_readiness_checks_database_and_cache(api_client):
    response = api_client.get(reverse("health-ready"))

    assert response.status_code == 200
    assert response.json()["checks"] == {"database": True, "redis": True}
