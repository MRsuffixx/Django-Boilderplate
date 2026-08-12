from __future__ import annotations

import pytest
from rest_framework.test import APIClient

from tests.factories import UserFactory


@pytest.fixture
def api_client() -> APIClient:
    return APIClient()


@pytest.fixture
def user(db):
    return UserFactory()


@pytest.fixture
def authenticated_client(api_client: APIClient, user):
    api_client.force_authenticate(user=user)
    return api_client
