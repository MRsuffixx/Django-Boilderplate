from __future__ import annotations

from collections.abc import Iterable

BASE_PERMISSIONS: dict[str, str] = {
    "users.view": "View users",
    "users.create": "Create users",
    "users.update": "Update users",
    "users.delete": "Delete users",
    "users.ban": "Ban and unban users",
    "roles.view": "View roles and permissions",
    "roles.manage": "Manage roles and permission assignments",
    "settings.view": "View runtime settings",
    "settings.update": "Update runtime settings",
    "audit.view": "View audit logs",
    "security_events.view": "View security events",
    "notifications.manage": "Manage notifications",
    "api_keys.manage": "Manage API keys for other users",
    "feature_flags.view": "View feature flags",
    "feature_flags.update": "Update feature flags",
    "webhooks.manage": "Manage webhook endpoints",
    "files.manage": "Manage uploaded files",
}

_registry: dict[str, str] = dict(BASE_PERMISSIONS)


def register_permissions(permissions: dict[str, str] | Iterable[tuple[str, str]]) -> None:
    for codename, description in dict(permissions).items():
        if codename in _registry and _registry[codename] != description:
            raise ValueError(f"Permission {codename!r} is already registered with a different description")
        _registry[codename] = description


def get_registered_permissions() -> dict[str, str]:
    return dict(sorted(_registry.items()))
