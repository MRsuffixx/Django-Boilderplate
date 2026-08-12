from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string


@dataclass(frozen=True, slots=True)
class EmailMessage:
    template: str
    recipient: str
    subject: str
    context: dict


class EmailService:
    @staticmethod
    def _task_context(value):
        if value is None or isinstance(value, (str, int, float, bool)):
            return value
        if isinstance(value, (date, datetime)):
            return value.isoformat()
        if isinstance(value, (UUID, Decimal)):
            return str(value)
        if isinstance(value, dict):
            return {str(key): EmailService._task_context(item) for key, item in value.items()}
        if isinstance(value, (list, tuple)):
            return [EmailService._task_context(item) for item in value]
        if hasattr(value, "email"):
            return {
                "id": str(value.pk),
                "email": value.email,
                "display_name": getattr(value, "display_name", value.email),
            }
        if hasattr(value, "identifier"):
            return {
                "identifier": value.identifier,
                "browser": value.browser,
                "operating_system": value.operating_system,
                "device": value.device,
                "ip_address": value.ip_address,
                "created_at": value.created_at.isoformat(),
            }
        if hasattr(value, "__dict__"):
            return {
                key: EmailService._task_context(item)
                for key, item in vars(value).items()
                if not key.startswith("_")
            }
        return str(value)

    @staticmethod
    def send(*, template: str, recipient: str, subject: str, context: dict | None = None) -> int:
        email_context = {
            "site_name": settings.SITE_NAME,
            "site_url": settings.SITE_URL,
            "support_email": settings.SUPPORT_EMAIL,
            **(context or {}),
        }
        text = render_to_string(f"emails/{template}.txt", email_context)
        html = render_to_string(f"emails/{template}.html", email_context)
        message = EmailMultiAlternatives(subject, text, settings.DEFAULT_FROM_EMAIL, [recipient])
        message.attach_alternative(html, "text/html")
        return message.send(fail_silently=False)

    @staticmethod
    def enqueue(*, template: str, recipient: str, subject: str, context: dict | None = None) -> None:
        if settings.ENABLE_CELERY and not settings.CELERY_TASK_ALWAYS_EAGER:
            from apps.core.tasks import send_templated_email

            send_templated_email.delay(
                template,
                recipient,
                subject,
                EmailService._task_context(context or {}),
            )
        else:
            EmailService.send(template=template, recipient=recipient, subject=subject, context=context)
