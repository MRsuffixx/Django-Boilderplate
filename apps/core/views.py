import logging

from django.conf import settings
from django.core.cache import cache
from django.db import connections
from django.db.utils import OperationalError
from django.http import JsonResponse

logger = logging.getLogger(__name__)


def live(_request):
    return JsonResponse({"status": "ok"})


def ready(_request):
    checks: dict[str, bool | str] = {
        "database": False,
        "redis": False if settings.REDIS_ENABLED else "disabled",
    }
    try:
        connections["default"].cursor().execute("SELECT 1")
        checks["database"] = True
    except OperationalError:
        logger.warning("health.database_unavailable")
    if settings.REDIS_ENABLED:
        try:
            marker = "ready"
            cache.set("healthcheck", marker, 5)
            checks["redis"] = cache.get("healthcheck") == marker
        except Exception:
            logger.warning("health.redis_unavailable", exc_info=True)
    is_ready = checks["database"] is True and checks["redis"] in {True, "disabled"}
    return JsonResponse(
        {"status": "ok" if is_ready else "unavailable", "checks": checks},
        status=200 if is_ready else 503,
    )


def health(request):
    return ready(request)
