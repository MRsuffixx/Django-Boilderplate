from django.core.exceptions import ImproperlyConfigured

from config.settings.base import *  # noqa: F403

DEBUG = False


def _require(name: str, value: object) -> None:
    if value in (None, "", [], {}):
        raise ImproperlyConfigured(f"{name} must be configured in production")


_require("SECRET_KEY", SECRET_KEY if SECRET_KEY != "unsafe-development-only-key" else "")  # noqa: F405
_require("ALLOWED_HOSTS", env("ALLOWED_HOSTS", default=""))  # noqa: F405
_require("TOTP_ENCRYPTION_KEY", TOTP_ENCRYPTION_KEY)  # noqa: F405
if ENABLE_API_KEYS:  # noqa: F405
    _require("API_KEY_PEPPER", API_KEY_PEPPER)  # noqa: F405
_require("DEFAULT_FROM_EMAIL", env("DEFAULT_FROM_EMAIL", default=""))  # noqa: F405
_require("EMAIL_BACKEND", env("EMAIL_BACKEND", default=""))  # noqa: F405

if len(SECRET_KEY) < 50:  # noqa: F405
    raise ImproperlyConfigured("Production SECRET_KEY must contain at least 50 characters")
if len(TOTP_ENCRYPTION_KEY) < 32:  # noqa: F405
    raise ImproperlyConfigured("Production TOTP_ENCRYPTION_KEY must contain at least 32 characters")
if ENABLE_API_KEYS and len(API_KEY_PEPPER) < 32:  # noqa: F405
    raise ImproperlyConfigured("Production API_KEY_PEPPER must contain at least 32 characters")
if EMAIL_BACKEND in {  # noqa: F405
    "django.core.mail.backends.console.EmailBackend",
    "django.core.mail.backends.locmem.EmailBackend",
    "django.core.mail.backends.dummy.EmailBackend",
}:
    raise ImproperlyConfigured("Production requires a delivery-capable email backend")
if not SITE_URL.startswith("https://"):  # noqa: F405
    raise ImproperlyConfigured("Production SITE_URL must use HTTPS")
if CELERY_ENABLED and CELERY_TASK_ALWAYS_EAGER:  # noqa: F405
    raise ImproperlyConfigured("CELERY_TASK_ALWAYS_EAGER must be false in production")
if TRUST_PROXY_HEADERS and not TRUSTED_PROXY_IPS:  # noqa: F405
    raise ImproperlyConfigured("TRUSTED_PROXY_IPS is required when proxy headers are trusted")
if env("STORAGE_BACKEND", default="local").lower() == "s3":  # noqa: F405
    _require("AWS_STORAGE_BUCKET_NAME", AWS_STORAGE_BUCKET_NAME)  # noqa: F405

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
