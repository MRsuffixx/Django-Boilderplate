from config.settings.base import *  # noqa: F403

DEBUG = env.bool("DEBUG", default=True)  # noqa: F405
EMAIL_BACKEND = env(  # noqa: F405
    "EMAIL_BACKEND", default="django.core.mail.backends.console.EmailBackend"
)
CELERY_TASK_ALWAYS_EAGER = env.bool("CELERY_TASK_ALWAYS_EAGER", default=True)  # noqa: F405

SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False
SECURE_SSL_REDIRECT = False

# Make local iteration deterministic even without Redis. Set REDIS_URL to exercise distributed state.
if not redis_url:  # noqa: F405
    CACHES = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}
