from django.core.exceptions import ImproperlyConfigured

from config.settings.base import *  # noqa: F403

DEBUG = False


def _require(name: str, value: object) -> None:
    if value in (None, "", [], {}):
        raise ImproperlyConfigured(f"{name} must be configured in production")


_require("SECRET_KEY", SECRET_KEY if SECRET_KEY != "unsafe-development-only-key" else "")  # noqa: F405
_require("ALLOWED_HOSTS", ALLOWED_HOSTS)  # noqa: F405
_require("DATABASE_URL", database_url)  # noqa: F405
_require("REDIS_URL", redis_url)  # noqa: F405
_require("TOTP_ENCRYPTION_KEY", TOTP_ENCRYPTION_KEY)  # noqa: F405
_require("API_KEY_PEPPER", API_KEY_PEPPER)  # noqa: F405

if DATABASES["default"]["ENGINE"] != "django.db.backends.postgresql":  # noqa: F405
    raise ImproperlyConfigured("Production requires PostgreSQL")

SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_SSL_REDIRECT = env.bool("SECURE_SSL_REDIRECT", default=True)  # noqa: F405
SECURE_HSTS_SECONDS = env.int("SECURE_HSTS_SECONDS", default=31536000)  # noqa: F405
SECURE_HSTS_INCLUDE_SUBDOMAINS = env.bool(  # noqa: F405
    "SECURE_HSTS_INCLUDE_SUBDOMAINS", default=True
)
SECURE_HSTS_PRELOAD = env.bool("SECURE_HSTS_PRELOAD", default=True)  # noqa: F405

if env.bool("TRUST_PROXY_HEADERS", default=False):  # noqa: F405
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    USE_X_FORWARDED_HOST = True

if not ENABLE_OPENAPI_IN_PRODUCTION:  # noqa: F405
    ENABLE_OPENAPI = False
