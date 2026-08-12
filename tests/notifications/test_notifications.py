import pytest
from django.urls import reverse
from django.utils import timezone

from apps.notifications.models import Notification
from tests.factories import UserFactory


pytestmark = pytest.mark.django_db


def test_notification_endpoints_are_owner_scoped(authenticated_client, user):
    mine = Notification.objects.create(user=user, type="info", title="Mine", message="Visible")
    other = Notification.objects.create(
        user=UserFactory(), type="info", title="Other", message="Hidden"
    )

    response = authenticated_client.get(reverse("notification-list"))

    ids = {item["id"] for item in response.data["data"]}
    assert str(mine.pk) in ids
    assert str(other.pk) not in ids


def test_mark_all_read_only_updates_current_user(authenticated_client, user):
    mine = Notification.objects.create(user=user, type="info", title="Mine", message="Visible")
    other = Notification.objects.create(
        user=UserFactory(), type="info", title="Other", message="Hidden"
    )

    response = authenticated_client.post(reverse("notification-mark-all-read"), format="json")

    mine.refresh_from_db()
    other.refresh_from_db()
    assert response.data["data"]["updated_count"] == 1
    assert mine.read_at <= timezone.now()
    assert other.read_at is None
