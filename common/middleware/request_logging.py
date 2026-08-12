from __future__ import annotations

import logging
import time

from common.context import user_id_context
from common.utils.network import get_client_ip

logger = logging.getLogger("request")


class RequestLoggingMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        started = time.monotonic()
        user_id = str(request.user.pk) if getattr(request, "user", None) and request.user.is_authenticated else "-"
        token = user_id_context.set(user_id)
        try:
            response = self.get_response(request)
            logger.info(
                "request.complete",
                extra={
                    "method": request.method,
                    "path": request.path,
                    "status_code": response.status_code,
                    "duration_ms": round((time.monotonic() - started) * 1000, 2),
                    "ip_address": get_client_ip(request),
                },
            )
            return response
        finally:
            user_id_context.reset(token)
