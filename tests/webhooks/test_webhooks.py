import hashlib
import hmac
import json
import socket

import pytest
from django.core.exceptions import ValidationError

from apps.webhooks.models import WebhookDelivery, WebhookEvent
from apps.webhooks.services import WebhookService

pytestmark = pytest.mark.django_db


def test_webhook_rejects_private_destination(monkeypatch):
    monkeypatch.setattr(
        socket,
        "getaddrinfo",
        lambda *args, **kwargs: [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("127.0.0.1", 443))],
    )

    with pytest.raises(ValidationError):
        WebhookService.validate_url("https://internal.example.test/hook")


def test_webhook_secret_is_encrypted_and_signature_is_verifiable(monkeypatch, user):
    monkeypatch.setattr(
        socket,
        "getaddrinfo",
        lambda *args, **kwargs: [
            (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", 443))
        ],
    )
    endpoint, secret = WebhookService.create_endpoint(
        owner=user,
        name="Receiver",
        url="https://example.test/hook",
        event_types=["example.created"],
    )
    event = WebhookEvent.objects.create(event_type="example.created", payload={"id": "123"})
    body = WebhookService.serialize_event(event)
    headers = WebhookService.signature_headers(endpoint=endpoint, event=event, body=body)

    timestamp = headers["X-Webhook-Timestamp"]
    expected = hmac.new(
        secret.encode(), timestamp.encode() + b"." + body, hashlib.sha256
    ).hexdigest()
    assert secret not in endpoint.encrypted_secret
    assert headers["X-Webhook-Signature"] == f"v1={expected}"
    assert json.loads(body)["type"] == "example.created"


def test_emit_selects_subscribed_endpoints_on_sqlite(monkeypatch, user):
    monkeypatch.setattr(
        socket,
        "getaddrinfo",
        lambda *args, **kwargs: [
            (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", 443))
        ],
    )
    matching, _ = WebhookService.create_endpoint(
        owner=user,
        name="Matching",
        url="https://matching.example.test/hook",
        event_types=["example.created"],
    )
    WebhookService.create_endpoint(
        owner=user,
        name="Other",
        url="https://other.example.test/hook",
        event_types=["example.updated"],
    )

    event = WebhookService.emit(event_type="example.created", payload={"id": "123"})

    assert list(WebhookDelivery.objects.filter(event=event).values_list("endpoint", flat=True)) == [
        matching.pk
    ]
