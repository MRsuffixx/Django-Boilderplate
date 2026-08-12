from django.core.management.base import BaseCommand
from django.db import transaction

from apps.authorization.models import Permission, Role, RolePermission
from apps.authorization.registry import get_registered_permissions

ROLE_DEFINITIONS = {
    "super-admin": {
        "name": "Super Admin",
        "description": "Full registered application access.",
        "priority": 1000,
        "permissions": "*",
    },
    "admin": {
        "name": "Admin",
        "description": "Administrative access except system role management.",
        "priority": 800,
        "permissions": "*",
    },
    "moderator": {
        "name": "Moderator",
        "description": "User safety and audit visibility.",
        "priority": 500,
        "permissions": [
            "users.view",
            "users.update",
            "users.ban",
            "audit.view",
            "security_events.view",
        ],
    },
    "user": {
        "name": "User",
        "description": "Default authenticated account role.",
        "priority": 100,
        "permissions": [],
    },
}


class Command(BaseCommand):
    help = "Idempotently synchronize registered permissions, system roles, settings, and flags."

    @transaction.atomic
    def handle(self, *args, **options):
        registry = get_registered_permissions()
        permission_rows = {}
        for codename, description in registry.items():
            permission, _ = Permission.objects.update_or_create(
                codename=codename,
                defaults={"description": description, "is_system": True},
            )
            permission_rows[codename] = permission

        for slug, definition in ROLE_DEFINITIONS.items():
            role, _ = Role.objects.update_or_create(
                slug=slug,
                defaults={
                    "name": definition["name"],
                    "description": definition["description"],
                    "priority": definition["priority"],
                    "is_system": True,
                },
            )
            desired = (
                set(registry)
                if definition["permissions"] == "*"
                else set(definition["permissions"])
            )
            for codename in desired:
                RolePermission.objects.get_or_create(
                    role=role, permission=permission_rows[codename]
                )

        from apps.core.models import FeatureFlag, Setting, SettingValueType

        Setting.objects.get_or_create(
            key="site.registration_enabled",
            defaults={
                "value": True,
                "value_type": SettingValueType.BOOLEAN,
                "group": "site",
                "is_public": True,
                "description": "Allow public user registration.",
            },
        )
        FeatureFlag.objects.get_or_create(
            key="registration.enabled",
            defaults={"enabled": True, "description": "Registration feature switch."},
        )
        self.stdout.write(
            self.style.SUCCESS(
                f"Synchronized {len(registry)} permissions and {len(ROLE_DEFINITIONS)} roles."
            )
        )
