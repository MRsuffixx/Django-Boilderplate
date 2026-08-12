from __future__ import annotations

from datetime import timedelta

import httpx
from celery import shared_task
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from apps.webhooks.models import DeliveryStatus, WebhookDelivery
from apps.webhooks.services import WebhookService


@shared_task(name="apps.webhooks.tasks.dispatch_pending_webhooks")
def dispatch_pending_webhooks() -> int:
    if not settings.ENABLE_WEBHOOKS:
        return 0
    now = timezone.now()
    ids = list(
        WebhookDelivery.objects.filter(status=DeliveryStatus.PENDING, endpoint__is_active=True)
        .filter(next_retry_at__isnull=True)
        .values_list("pk", flat=True)[:100]
    )
    ids += list(
        WebhookDelivery.objects.filter(
            status=DeliveryStatus.FAILED, next_retry_at__lte=now, endpoint__is_active=True
        ).values_list("pk", flat=True)[: max(0, 100 - len(ids))]
    )
    ids += list(
        WebhookDelivery.objects.filter(
            status=DeliveryStatus.PROCESSING,
            last_attempt_at__lt=now - timedelta(minutes=15),
            endpoint__is_active=True,
        ).values_list("pk", flat=True)[: max(0, 100 - len(ids))]
    )
    for delivery_id in ids:
        deliver_webhook.delay(str(delivery_id))
    return len(ids)


@shared_task(name="apps.webhooks.tasks.deliver_webhook", max_retries=0)
def deliver_webhook(delivery_id: str) -> None:
    with transaction.atomic():
        delivery = (
            WebhookDelivery.objects.select_for_update()
            .select_related("endpoint", "event")
            .get(pk=delivery_id)
        )
        if delivery.status in {DeliveryStatus.SUCCEEDED, DeliveryStatus.ABANDONED}:
            return
        if (
            delivery.status == DeliveryStatus.PROCESSING
            and delivery.last_attempt_at
            and delivery.last_attempt_at > timezone.now() - timedelta(minutes=15)
        ):
            return
        delivery.attempt_count += 1
        delivery.last_attempt_at = timezone.now()
        delivery.status = DeliveryStatus.PROCESSING
        delivery.save(update_fields=["attempt_count", "last_attempt_at", "status"])

    try:
        WebhookService.validate_url(delivery.endpoint.url)
        body = WebhookService.serialize_event(delivery.event)
        headers = WebhookService.signature_headers(
            endpoint=delivery.endpoint, event=delivery.event, body=body
        )
        with httpx.Client(timeout=10, follow_redirects=False) as client:
            response = client.post(delivery.endpoint.url, content=body, headers=headers)
        delivery.response_code = response.status_code
        delivery.response_body = response.text[:4096]
        if 200 <= response.status_code < 300:
            delivery.status = DeliveryStatus.SUCCEEDED
            delivery.next_retry_at = None
        else:
            raise httpx.HTTPStatusError(
                "Non-success status", request=response.request, response=response
            )
    except (httpx.HTTPError, ValidationError):
        if delivery.attempt_count >= 8:
            delivery.status = DeliveryStatus.ABANDONED
            delivery.next_retry_at = None
        else:
            delivery.status = DeliveryStatus.FAILED
            delivery.next_retry_at = timezone.now() + timedelta(
                seconds=min(3600, 30 * (2 ** (delivery.attempt_count - 1)))
            )
    delivery.save(
        update_fields=[
            "response_code",
            "response_body",
            "status",
            "next_retry_at",
        ]
    )
