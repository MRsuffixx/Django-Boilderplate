from __future__ import annotations

import logging
from typing import Any

from django.core.exceptions import PermissionDenied as DjangoPermissionDenied
from django.http import Http404
from rest_framework import exceptions, status
from rest_framework.response import Response
from rest_framework.views import exception_handler

logger = logging.getLogger(__name__)


class APIException(exceptions.APIException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_code = "BAD_REQUEST"
    default_detail = "The request could not be processed."

    def __init__(
        self, detail=None, *, code: str | None = None, status_code: int | None = None, fields=None
    ):
        super().__init__(detail or self.default_detail, code=code or self.default_code)
        if status_code is not None:
            self.status_code = status_code
        self.api_code = code or self.default_code
        self.fields = fields


def _error_code(exc: Exception, response: Response) -> str:
    mapping = {
        exceptions.ValidationError: "VALIDATION_ERROR",
        exceptions.NotAuthenticated: "AUTHENTICATION_REQUIRED",
        exceptions.AuthenticationFailed: "AUTHENTICATION_FAILED",
        exceptions.PermissionDenied: "PERMISSION_DENIED",
        exceptions.NotFound: "RESOURCE_NOT_FOUND",
        exceptions.Throttled: "RATE_LIMITED",
        Http404: "RESOURCE_NOT_FOUND",
        DjangoPermissionDenied: "PERMISSION_DENIED",
    }
    if isinstance(exc, APIException):
        return exc.api_code
    for klass, code in mapping.items():
        if isinstance(exc, klass):
            return code
    return "INTERNAL_ERROR" if response.status_code >= 500 else "BAD_REQUEST"


def api_exception_handler(exc: Exception, context: dict[str, Any]) -> Response:
    response = exception_handler(exc, context)
    request = context.get("request")
    request_id = getattr(request, "request_id", None)

    if response is None:
        logger.exception("api.unhandled_exception", exc_info=exc)
        return Response(
            {
                "success": False,
                "data": None,
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": "An unexpected error occurred.",
                    "fields": {},
                    "request_id": request_id,
                },
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    code = _error_code(exc, response)
    fields = {}
    message = "The request could not be processed."
    if isinstance(exc, exceptions.ValidationError):
        fields = response.data
        message = "Validation failed."
    elif isinstance(response.data, dict) and "detail" in response.data:
        message = str(response.data["detail"])
    elif isinstance(response.data, list):
        fields = {"non_field_errors": response.data}
    elif isinstance(response.data, dict):
        fields = response.data
    if isinstance(exc, APIException):
        message = str(exc.detail)
        fields = exc.fields or fields

    response.data = {
        "success": False,
        "data": None,
        "error": {"code": code, "message": message, "fields": fields, "request_id": request_id},
    }
    return response
