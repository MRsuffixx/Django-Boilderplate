from __future__ import annotations

from dataclasses import dataclass

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

            send_templated_email.delay(template, recipient, subject, context or {})
        else:
            EmailService.send(template=template, recipient=recipient, subject=subject, context=context)
