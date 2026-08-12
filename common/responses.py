from rest_framework.response import Response


def success_response(data=None, *, meta=None, status=200, headers=None) -> Response:
    return Response(
        {"success": True, "data": data, "meta": meta or {}, "error": None},
        status=status,
        headers=headers,
    )
