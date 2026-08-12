from __future__ import annotations

import re
import uuid

from common.context import request_id_context

VALID_REQUEST_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,63}$")


class RequestIDMiddleware:
    header = "HTTP_X_REQUEST_ID"

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        incoming = request.META.get(self.header, "")
        request_id = incoming if VALID_REQUEST_ID.fullmatch(incoming) else str(uuid.uuid4())
        request.request_id = request_id
        token = request_id_context.set(request_id)
        try:
            response = self.get_response(request)
            response["X-Request-ID"] = request_id
            return response
        finally:
            request_id_context.reset(token)
