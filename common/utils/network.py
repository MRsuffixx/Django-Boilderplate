from __future__ import annotations

import ipaddress

from django.conf import settings


def get_client_ip(request) -> str | None:
    remote = request.META.get("REMOTE_ADDR")
    trusted_proxies = set(getattr(settings, "TRUSTED_PROXY_IPS", []))
    if getattr(settings, "TRUST_PROXY_HEADERS", False) and remote in trusted_proxies:
        forwarded = request.META.get("HTTP_X_FORWARDED_FOR", "")
        candidate = forwarded.split(",")[0].strip() if forwarded else remote
    else:
        candidate = remote
    if not candidate:
        return None
    try:
        return str(ipaddress.ip_address(candidate))
    except ValueError:
        return None
