import logging

from django.core.cache import cache
from django.db import connections
from django.db.utils import OperationalError
from django.http import JsonResponse

logger = logging.getLogger(__name__)


def live(_request):
    return JsonResponse({"status": "ok"})


def ready(_request):
    checks = {"database": False, "redis": False}
    try:
        connections["default"].cursor().execute("SELECT 1")
        checks["database"] = True
    except OperationalError:
        logger.warning("health.database_unavailable")
    try:
        marker = "ready"
        cache.set("healthcheck", marker, 5)
        checks["redis"] = cache.get("healthcheck") == marker
    except Exception:
        logger.warning("health.cache_unavailable", exc_info=True)
    is_ready = all(checks.values())
    return JsonResponse(
        {"status": "ok" if is_ready else "unavailable", "checks": checks},
        status=200 if is_ready else 503,
    )


def health(request):
    return ready(request)
