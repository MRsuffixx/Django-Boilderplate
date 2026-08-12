from celery import shared_task

from common.services.email import EmailService


@shared_task(
    name="apps.core.tasks.send_templated_email",
    autoretry_for=(OSError, ConnectionError),
    retry_backoff=True,
    retry_jitter=True,
    max_retries=5,
)
def send_templated_email(template: str, recipient: str, subject: str, context: dict) -> int:
    return EmailService.send(
        template=template, recipient=recipient, subject=subject, context=context
    )
