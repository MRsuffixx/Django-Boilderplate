from __future__ import annotations

import hashlib
import json
from datetime import timedelta
from functools import wraps

from django.db import IntegrityError, transaction
from django.utils import timezone
from rest_framework.response import Response

from apps.core.models import IdempotencyRecord
from common.crypto import keyed_hash
from common.exceptions import APIException


def idempotent(*, ttl: timedelta = timedelta(hours=24)):
    """Opt-in decorator for authenticated state-changing DRF view methods."""

    def decorator(method):
        @wraps(method)
        def wrapped(view, request, *args, **kwargs):
            raw_key = request.headers.get("Idempotency-Key", "")
            if not raw_key:
                return method(view, request, *args, **kwargs)
            if not request.user.is_authenticated:
                raise APIException("Authentication is required for idempotency.", code="AUTHENTICATION_REQUIRED", status_code=401)
            if len(raw_key) > 255:
                raise APIException("Invalid Idempotency-Key.", code="VALIDATION_ERROR")
            key_hash = keyed_hash(raw_key, purpose="idempotency")
            body = request.body or b""
            request_hash = hashlib.sha256(request.method.encode() + request.path.encode() + body).hexdigest()
            with transaction.atomic():
                record = IdempotencyRecord.objects.select_for_update().filter(user=request.user, key_hash=key_hash).first()
                if record:
                    if record.request_hash != request_hash:
                        raise APIException("This Idempotency-Key was used for a different request.", code="CONFLICT", status_code=409)
                    if record.response_status is None:
                        raise APIException("A request with this Idempotency-Key is in progress.", code="CONFLICT", status_code=409)
                    return Response(record.response_body, status=record.response_status, headers={"Idempotent-Replayed": "true"})
                try:
                    record = IdempotencyRecord.objects.create(
                        user=request.user,
                        key_hash=key_hash,
                        request_method=request.method,
                        request_path=request.path,
                        request_hash=request_hash,
                        expires_at=timezone.now() + ttl,
                    )
                except IntegrityError as exc:
                    raise APIException("A request with this Idempotency-Key is in progress.", code="CONFLICT", status_code=409) from exc
                response = method(view, request, *args, **kwargs)
                response.render()
                try:
                    json.dumps(response.data)
                except (TypeError, ValueError) as exc:
                    raise RuntimeError("Idempotent responses must be JSON serializable") from exc
                record.response_status = response.status_code
                record.response_body = response.data
                record.save(update_fields=["response_status", "response_body"])
                return response

        return wrapped

    return decorator
