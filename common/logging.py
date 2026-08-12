from __future__ import annotations

import logging
import re
from typing import Any

from pythonjsonlogger.json import JsonFormatter

from common.context import request_id_context, user_id_context

SENSITIVE_KEY = re.compile(
    r"password|authorization|cookie|token|secret|api[_-]?key|totp|recovery[_-]?code",
    re.IGNORECASE,
)


def sanitize(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: "[REDACTED]" if SENSITIVE_KEY.search(str(key)) else sanitize(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [sanitize(item) for item in value]
    return value


class RequestContextFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = request_id_context.get()
        record.user_id = user_id_context.get()
        return True


class SanitizingJsonFormatter(JsonFormatter):
    def __init__(self, *args, **kwargs):
        super().__init__(
            "%(asctime)s %(levelname)s %(name)s %(message)s %(request_id)s %(user_id)s",
            *args,
            **kwargs,
        )

    def process_log_record(self, log_record: dict[str, Any]) -> dict[str, Any]:
        return sanitize(log_record)
