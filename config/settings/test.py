from config.settings.base import *  # noqa: F403

DEBUG = False
SECRET_KEY = "test-only-secret-key-not-for-production-and-long-enough-for-jwt-hmac"
DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:"}}
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True
CACHES = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}
TOTP_ENCRYPTION_KEY = "test-totp-encryption-key"
API_KEY_PEPPER = "test-api-key-pepper"
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.InMemoryStorage"},
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
}
MIDDLEWARE = [
    middleware for middleware in MIDDLEWARE if middleware != "whitenoise.middleware.WhiteNoiseMiddleware"
]
