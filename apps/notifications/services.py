from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from django.conf import settings
from django.db import transaction

from apps.notifications.models import Notification
from common.services.email import EmailService


@dataclass(frozen=True, slots=True)
class NotificationMessage:
    type: str
    title: str
    message: str
    data: dict
    expires_at: datetime | None = None


class NotificationService:
    @staticmethod
    def notify(
        *, user, message: NotificationMessage, channels: tuple[str, ...] = ("in_app",)
    ) -> Notification | None:
        notification = None
        if settings.ENABLE_NOTIFICATIONS and "in_app" in channels:
            notification = Notification.objects.create(
                user=user,
                type=message.type,
                title=message.title,
                message=message.message,
                data=message.data,
                expires_at=message.expires_at,
            )
        if "email" in channels and user.preferences.email_notifications:
            transaction.on_commit(
                lambda: EmailService.enqueue(
                    template="notification",
                    recipient=user.email,
                    subject=message.title,
                    context={"user": user, "notification": message},
                )
            )
        return notification
