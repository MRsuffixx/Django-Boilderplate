import pytest
from django.core.management import call_command

from apps.authorization.models import Permission, Role
from apps.authorization.registry import get_registered_permissions

pytestmark = pytest.mark.django_db


def test_bootstrap_is_idempotent_and_additive():
    call_command("bootstrap", verbosity=0)
    call_command("bootstrap", verbosity=0)

    assert Permission.objects.count() == len(get_registered_permissions())
    assert set(Role.objects.values_list("slug", flat=True)) == {
        "super-admin",
        "admin",
        "moderator",
        "user",
    }
