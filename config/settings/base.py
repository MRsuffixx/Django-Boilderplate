from __future__ import annotations

import importlib.util
from datetime import timedelta
from pathlib import Path

import environ
from django.core.exceptions import ImproperlyConfigured

from config.settings.database import build_database_config

BASE_DIR = Path(__file__).resolve().parents[2]
env = environ.Env()
env_file = BASE_DIR / ".env"
if env_file.exists():
    environ.Env.read_env(env_file)

APP_ENV = env("APP_ENV", default="development")
DEBUG = env.bool("DEBUG", default=False)
SECRET_KEY = env("SECRET_KEY", default="unsafe-development-only-key")

APP_NAME = env("APP_NAME", default="Django Foundation")
SITE_NAME = env("SITE_NAME", default=APP_NAME)
SITE_URL = env("SITE_URL", default="http://localhost:8000").rstrip("/")
SUPPORT_EMAIL = env("SUPPORT_EMAIL", default="support@localhost")
DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL", default=f"{SITE_NAME} <noreply@localhost>")

ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", default=["localhost", "127.0.0.1"])

DJANGO_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
]
THIRD_PARTY_APPS = [
    "corsheaders",
    "django_filters",
    "drf_spectacular",
    "rest_framework",
    "rest_framework_simplejwt.token_blacklist",
]
LOCAL_APPS = [
    "apps.core",
    "apps.accounts",
    "apps.authentication",
    "apps.authorization",
    "apps.security",
    "apps.audit",
    "apps.notifications",
    "apps.files",
    "apps.api_keys",
    "apps.webhooks",
    "apps.api",
]
INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "common.middleware.request_id.RequestIDMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "apps.authentication.middleware.UserSessionMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "common.middleware.security_headers.ContentSecurityPolicyMiddleware",
    "common.middleware.request_logging.RequestLoggingMiddleware",
]

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "common.context_processors.branding",
            ],
        },
    },
]

DATABASES = build_database_config(env=env, base_dir=BASE_DIR)
DATABASE_ENGINE = (
    "postgresql"
    if DATABASES["default"]["ENGINE"] == "django.db.backends.postgresql"
    else "sqlite"
)

REDIS_ENABLED = env.bool("REDIS_ENABLED", default=False)
REDIS_URL = env("REDIS_URL", default="redis://localhost:6379/0").strip()
if REDIS_ENABLED:
    if not REDIS_URL:
        raise ImproperlyConfigured("REDIS_URL is required when REDIS_ENABLED=true")
    if importlib.util.find_spec("django_redis") is None:
        raise ImproperlyConfigured(
            'REDIS_ENABLED=true requires the optional ".[redis]" dependency.'
        )
    CACHES = {
        "default": {
            "BACKEND": "django_redis.cache.RedisCache",
            "LOCATION": REDIS_URL,
            "OPTIONS": {"CLIENT_CLASS": "django_redis.client.DefaultClient"},
            "KEY_PREFIX": APP_NAME.lower().replace(" ", "_"),
        }
    }
else:
    CACHES = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}

AUTH_USER_MODEL = "accounts.User"
AUTHENTICATION_BACKENDS = ["apps.authentication.backends.EmailOrUsernameBackend"]
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.Argon2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2SHA1PasswordHasher",
]
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
        "OPTIONS": {"min_length": 12},
    },
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]
PASSWORD_RESET_TIMEOUT = env.int("PASSWORD_RESET_TIMEOUT_SECONDS", default=3600)

LANGUAGE_CODE = env("DEFAULT_LANGUAGE", default="en")
LANGUAGES = [("en", "English"), ("tr", "Türkçe")]
TIME_ZONE = env("TIME_ZONE", default="UTC")
USE_I18N = True
USE_TZ = True
LOCALE_PATHS = [BASE_DIR / "locale"]

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"
STATICFILES_DIRS = [BASE_DIR / "static"]
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
}
if env("STORAGE_BACKEND", default="local").lower() == "s3":
    if importlib.util.find_spec("storages") is None:
        raise ImproperlyConfigured(
            'STORAGE_BACKEND=s3 requires the optional ".[s3]" dependency.'
        )
    STORAGES["default"] = {"BACKEND": "storages.backends.s3.S3Storage"}
    AWS_ACCESS_KEY_ID = env("AWS_ACCESS_KEY_ID", default="")
    AWS_SECRET_ACCESS_KEY = env("AWS_SECRET_ACCESS_KEY", default="")
    AWS_STORAGE_BUCKET_NAME = env("AWS_STORAGE_BUCKET_NAME", default="")
    AWS_S3_ENDPOINT_URL = env("AWS_S3_ENDPOINT_URL", default=None)
    AWS_S3_REGION_NAME = env("AWS_S3_REGION_NAME", default=None)
    AWS_S3_CUSTOM_DOMAIN = env("AWS_S3_CUSTOM_DOMAIN", default=None)
    AWS_QUERYSTRING_AUTH = env.bool("AWS_QUERYSTRING_AUTH", default=True)
    AWS_DEFAULT_ACL = None
    AWS_S3_FILE_OVERWRITE = False

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "apps.api_keys.authentication.APIKeyAuthentication",
        "apps.authentication.jwt.StatusAwareJWTAuthentication",
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
        "apps.api_keys.permissions.HasAPIKeyScope",
    ],
    "DEFAULT_PAGINATION_CLASS": "common.pagination.StandardPagination",
    "PAGE_SIZE": 25,
    "EXCEPTION_HANDLER": "common.exceptions.handler.api_exception_handler",
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_FILTER_BACKENDS": [
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.SearchFilter",
        "rest_framework.filters.OrderingFilter",
    ],
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {
        "anon": env("THROTTLE_ANON", default="100/hour"),
        "user": env("THROTTLE_USER", default="1000/hour"),
        "login": env("THROTTLE_LOGIN", default="10/minute"),
        "register": env("THROTTLE_REGISTER", default="5/hour"),
        "password_reset": env("THROTTLE_PASSWORD_RESET", default="5/hour"),
        "email_verification": env("THROTTLE_EMAIL_VERIFICATION", default="5/hour"),
        "api_key": env("THROTTLE_API_KEY", default="600/hour"),
    },
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=env.int("ACCESS_TOKEN_MINUTES", default=10)),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=env.int("REFRESH_TOKEN_DAYS", default=7)),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "UPDATE_LAST_LOGIN": False,
    "AUTH_HEADER_TYPES": ("Bearer",),
    "SIGNING_KEY": SECRET_KEY,
}

SPECTACULAR_SETTINGS = {
    "TITLE": f"{APP_NAME} API",
    "DESCRIPTION": "Versioned API for the reusable Django application foundation.",
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "COMPONENT_SPLIT_REQUEST": True,
}

CORS_ALLOWED_ORIGINS = env.list("CORS_ALLOWED_ORIGINS", default=[])
CORS_ALLOW_CREDENTIALS = True
CSRF_TRUSTED_ORIGINS = env.list("CSRF_TRUSTED_ORIGINS", default=[])
CSRF_COOKIE_HTTPONLY = False
CSRF_COOKIE_SAMESITE = "Lax"
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
X_FRAME_OPTIONS = "DENY"
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "strict-origin-when-cross-origin"
CONTENT_SECURITY_POLICY = env(
    "CONTENT_SECURITY_POLICY",
    default="default-src 'self'; img-src 'self' data: https:; style-src 'self' 'unsafe-inline'; script-src 'self'",
)
TRUST_PROXY_HEADERS = env.bool("TRUST_PROXY_HEADERS", default=False)
TRUSTED_PROXY_IPS = env.list("TRUSTED_PROXY_IPS", default=[])

EMAIL_BACKEND = env("EMAIL_BACKEND", default="django.core.mail.backends.console.EmailBackend")
EMAIL_HOST = env("EMAIL_HOST", default="localhost")
EMAIL_PORT = env.int("EMAIL_PORT", default=1025)
EMAIL_HOST_USER = env("EMAIL_HOST_USER", default="")
EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD", default="")
EMAIL_USE_TLS = env.bool("EMAIL_USE_TLS", default=False)
EMAIL_USE_SSL = env.bool("EMAIL_USE_SSL", default=False)
EMAIL_TIMEOUT = 10

CELERY_ENABLED = env.bool("CELERY_ENABLED", default=False)
CELERY_BROKER_URL = env("CELERY_BROKER_URL", default="").strip()
CELERY_RESULT_BACKEND = env("CELERY_RESULT_BACKEND", default="").strip()
if CELERY_ENABLED:
    if importlib.util.find_spec("celery") is None:
        raise ImproperlyConfigured(
            'CELERY_ENABLED=true requires the optional ".[celery]" dependency.'
        )
    if not CELERY_BROKER_URL:
        raise ImproperlyConfigured("CELERY_BROKER_URL is required when CELERY_ENABLED=true")
    redis_backends = ("redis://", "rediss://")
    if CELERY_BROKER_URL.startswith(redis_backends) and not REDIS_ENABLED:
        raise ImproperlyConfigured(
            "Enable Redis when CELERY_BROKER_URL uses Redis, or configure another broker"
        )
    if CELERY_RESULT_BACKEND.startswith(redis_backends) and not REDIS_ENABLED:
        raise ImproperlyConfigured(
            "Enable Redis when CELERY_RESULT_BACKEND uses Redis, or configure another backend"
        )
else:
    CELERY_BROKER_URL = CELERY_BROKER_URL or "memory://"
    CELERY_RESULT_BACKEND = CELERY_RESULT_BACKEND or "cache+memory://"
CELERY_TASK_ALWAYS_EAGER = env.bool("CELERY_TASK_ALWAYS_EAGER", default=False)
CELERY_TASK_EAGER_PROPAGATES = True
CELERY_TASK_SERIALIZER = "json"
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = TIME_ZONE
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_ACKS_LATE = True
CELERY_WORKER_PREFETCH_MULTIPLIER = 1
CELERY_BEAT_SCHEDULE = {
    "cleanup-sessions-daily": {
        "task": "apps.authentication.tasks.cleanup_sessions",
        "schedule": 86400,
    },
    "cleanup-tokens-daily": {"task": "apps.authentication.tasks.cleanup_tokens", "schedule": 86400},
    "cleanup-notifications-daily": {
        "task": "apps.notifications.tasks.cleanup_notifications",
        "schedule": 86400,
    },
    "expire-bans-hourly": {"task": "apps.accounts.tasks.expire_temporary_bans", "schedule": 3600},
    "cleanup-files-daily": {"task": "apps.files.tasks.cleanup_unused_files", "schedule": 86400},
    "cleanup-audit-daily": {"task": "apps.audit.tasks.cleanup_audit_logs", "schedule": 86400},
    "cleanup-login-attempts-daily": {
        "task": "apps.security.tasks.cleanup_login_attempts",
        "schedule": 86400,
    },
    "dispatch-webhooks": {"task": "apps.webhooks.tasks.dispatch_pending_webhooks", "schedule": 60},
}

ENABLE_NOTIFICATIONS = env.bool("ENABLE_NOTIFICATIONS", default=True)
ENABLE_API_KEYS = env.bool("ENABLE_API_KEYS", default=True)
ENABLE_TWO_FACTOR = env.bool("ENABLE_TWO_FACTOR", default=True)
ENABLE_WEBHOOKS = env.bool("ENABLE_WEBHOOKS", default=False)
ENABLE_OPENAPI = env.bool("ENABLE_OPENAPI", default=True)
ENABLE_OPENAPI_IN_PRODUCTION = env.bool("ENABLE_OPENAPI_IN_PRODUCTION", default=False)

LOGIN_MAX_ATTEMPTS = env.int("LOGIN_MAX_ATTEMPTS", default=5)
LOGIN_LOCKOUT_SECONDS = env.int("LOGIN_LOCKOUT_SECONDS", default=300)
LOGIN_MAX_BACKOFF_SECONDS = env.int("LOGIN_MAX_BACKOFF_SECONDS", default=3600)
TOTP_ENCRYPTION_KEY = env("TOTP_ENCRYPTION_KEY", default="")
API_KEY_PEPPER = env("API_KEY_PEPPER", default="")
API_KEY_AVAILABLE_SCOPES = env.list(
    "API_KEY_AVAILABLE_SCOPES",
    default=["profile.read", "profile.write", "notifications.read", "notifications.write"],
)
MAX_UPLOAD_SIZE = env.int("MAX_UPLOAD_SIZE", default=10 * 1024 * 1024)
MAX_IMAGE_PIXELS = env.int("MAX_IMAGE_PIXELS", default=25_000_000)
SESSION_RETENTION_DAYS = env.int("SESSION_RETENTION_DAYS", default=30)
TOKEN_RETENTION_DAYS = env.int("TOKEN_RETENTION_DAYS", default=7)
NOTIFICATION_RETENTION_DAYS = env.int("NOTIFICATION_RETENTION_DAYS", default=90)
AUDIT_RETENTION_DAYS = env.int("AUDIT_RETENTION_DAYS", default=0)
FILE_RETENTION_DAYS = env.int("FILE_RETENTION_DAYS", default=7)
WEBHOOK_RETENTION_DAYS = env.int("WEBHOOK_RETENTION_DAYS", default=30)

LOG_LEVEL = env("LOG_LEVEL", default="INFO")
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "filters": {"request_context": {"()": "common.logging.RequestContextFilter"}},
    "formatters": {
        "readable": {"format": "%(levelname)s %(asctime)s %(name)s %(request_id)s %(message)s"},
        "json": {"()": "common.logging.SanitizingJsonFormatter"},
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "filters": ["request_context"],
            "formatter": "readable" if DEBUG else "json",
        }
    },
    "root": {"handlers": ["console"], "level": LOG_LEVEL},
    "loggers": {
        "django.server": {"handlers": ["console"], "level": LOG_LEVEL, "propagate": False},
        "django.security.DisallowedHost": {
            "handlers": ["console"],
            "level": "WARNING",
            "propagate": False,
        },
    },
}

ENABLE_SENTRY = env.bool("ENABLE_SENTRY", default=False)
SENTRY_DSN = env("SENTRY_DSN", default="")
if ENABLE_SENTRY and SENTRY_DSN:
    try:
        import sentry_sdk
        from sentry_sdk.integrations.django import DjangoIntegration
    except ImportError as exc:
        raise ImproperlyConfigured("Install the production extra to enable Sentry") from exc
    sentry_integrations = [DjangoIntegration()]
    if CELERY_ENABLED:
        try:
            from sentry_sdk.integrations.celery import CeleryIntegration
        except ImportError as exc:
            raise ImproperlyConfigured(
                "The Sentry Celery integration requires the celery optional dependency"
            ) from exc
        sentry_integrations.append(CeleryIntegration())
    sentry_sdk.init(
        dsn=SENTRY_DSN,
        integrations=sentry_integrations,
        send_default_pii=False,
        traces_sample_rate=env.float("SENTRY_TRACES_SAMPLE_RATE", default=0.0),
        environment=APP_ENV,
    )
