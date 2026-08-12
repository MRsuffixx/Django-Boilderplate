from __future__ import annotations

import base64
import hashlib
import hmac
import secrets

from cryptography.fernet import Fernet, InvalidToken
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured


def _key_material(purpose: str) -> bytes:
    configured = settings.TOTP_ENCRYPTION_KEY or settings.SECRET_KEY
    if settings.APP_ENV == "production" and not settings.TOTP_ENCRYPTION_KEY:
        raise ImproperlyConfigured("TOTP_ENCRYPTION_KEY is required in production")
    return hashlib.sha256(f"{purpose}:{configured}".encode()).digest()


def encrypt_value(value: str, *, purpose: str) -> str:
    key = base64.urlsafe_b64encode(_key_material(purpose))
    return Fernet(key).encrypt(value.encode()).decode()


def decrypt_value(value: str, *, purpose: str) -> str:
    key = base64.urlsafe_b64encode(_key_material(purpose))
    try:
        return Fernet(key).decrypt(value.encode()).decode()
    except InvalidToken as exc:
        raise ValueError("Encrypted value could not be decrypted") from exc


def keyed_hash(value: str, *, purpose: str, pepper: str | None = None) -> str:
    secret = pepper or settings.SECRET_KEY
    return hmac.new(
        hashlib.sha256(f"{purpose}:{secret}".encode()).digest(),
        value.encode(),
        hashlib.sha256,
    ).hexdigest()


def generate_token(bytes_count: int = 32) -> str:
    return secrets.token_urlsafe(bytes_count)


def secure_compare(left: str, right: str) -> bool:
    return hmac.compare_digest(left, right)
