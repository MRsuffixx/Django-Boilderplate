import pytest
from django.core import mail

from apps.notifications.services import NotificationMessage, NotificationService

pytestmark = pytest.mark.django_db


def test_notification_service_supports_in_app_and_email_channels(
    user, django_capture_on_commit_callbacks
):
    with django_capture_on_commit_callbacks(execute=True):
        notification = NotificationService.notify(
            user=user,
            message=NotificationMessage(
                type="security.notice",
                title="Review activity",
                message="A security event requires review.",
                data={"severity": "high"},
            ),
            channels=("in_app", "email"),
        )

    assert notification.user == user
    assert notification.data == {"severity": "high"}
    assert mail.outbox[-1].to == [user.email]
    assert "Review activity" in mail.outbox[-1].subject
