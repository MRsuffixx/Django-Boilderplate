import pytest
from django.urls import reverse


pytestmark = pytest.mark.django_db


def test_validation_errors_have_stable_envelope_and_request_id(api_client):
    response = api_client.post(
        reverse("register"),
        {},
        format="json",
        HTTP_X_REQUEST_ID="validation-test",
    )

    assert response.status_code == 400
    assert response.data["success"] is False
    assert response.data["error"]["code"] == "VALIDATION_ERROR"
    assert response.data["error"]["request_id"] == "validation-test"
    assert "email" in response.data["error"]["fields"]
