from __future__ import annotations

import hashlib
import hmac
import ipaddress
import json
import socket
import time
from urllib.parse import urlparse

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import transaction

from apps.webhooks.models import WebhookDelivery, WebhookEndpoint, WebhookEvent
from common.crypto import decrypt_value, encrypt_value, generate_token, keyed_hash


class WebhookService:
    @staticmethod
    def validate_url(url: str) -> None:
        parsed = urlparse(url)
        if parsed.scheme not in (
            {"https"} if settings.APP_ENV == "production" else {"http", "https"}
        ):
            raise ValidationError("Webhook URLs must use an allowed HTTP scheme.")
        if not parsed.hostname or parsed.username or parsed.password:
            raise ValidationError("Webhook URL is invalid.")
        try:
            addresses = {
                item[4][0] for item in socket.getaddrinfo(parsed.hostname, parsed.port or 443)
            }
        except socket.gaierror as exc:
            raise ValidationError("Webhook hostname could not be resolved.") from exc
        for address in addresses:
            ip = ipaddress.ip_address(address)
            if not ip.is_global:
                raise ValidationError(
                    "Webhook URLs cannot resolve to private or reserved addresses."
                )

    @classmethod
    @transaction.atomic
    def create_endpoint(
        cls, *, owner, name: str, url: str, event_types: list[str]
    ) -> tuple[WebhookEndpoint, str]:
        cls.validate_url(url)
        secret = generate_token(32)
        endpoint = WebhookEndpoint.objects.create(
            owner=owner,
            name=name,
            url=url,
            event_types=sorted(set(event_types)),
            secret_hash=keyed_hash(secret, purpose="webhook-secret"),
            encrypted_secret=encrypt_value(secret, purpose="webhook-secret"),
        )
        return endpoint, secret

    @staticmethod
    @transaction.atomic
    def emit(*, event_type: str, payload: dict) -> WebhookEvent:
        event = WebhookEvent.objects.create(event_type=event_type, payload=payload)
        endpoints = WebhookEndpoint.objects.filter(
            is_active=True, event_types__contains=[event_type]
        )
        WebhookDelivery.objects.bulk_create(
            [WebhookDelivery(endpoint=endpoint, event=event) for endpoint in endpoints]
        )
        return event

    @classmethod
    def signature_headers(
        cls, *, endpoint: WebhookEndpoint, event: WebhookEvent, body: bytes
    ) -> dict[str, str]:
        secret = decrypt_value(endpoint.encrypted_secret, purpose="webhook-secret")
        timestamp = str(int(time.time()))
        signature = hmac.new(
            secret.encode(), timestamp.encode() + b"." + body, hashlib.sha256
        ).hexdigest()
        return {
            "Content-Type": "application/json",
            "User-Agent": f"{settings.APP_NAME}-Webhooks/1.0",
            "X-Webhook-ID": str(event.pk),
            "X-Webhook-Timestamp": timestamp,
            "X-Webhook-Signature": f"v1={signature}",
        }

    @staticmethod
    def serialize_event(event: WebhookEvent) -> bytes:
        return json.dumps(
            {
                "id": str(event.pk),
                "type": event.event_type,
                "created_at": event.created_at.isoformat(),
                "data": event.payload,
            },
            separators=(",", ":"),
            sort_keys=True,
        ).encode()
