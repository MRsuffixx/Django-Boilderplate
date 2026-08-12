from __future__ import annotations

import factory
from django.utils import timezone

from apps.accounts.models import AccountStatus, User
from apps.authorization.models import Permission, Role


class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = User
        skip_postgeneration_save = True

    email = factory.Sequence(lambda number: f"user{number}@example.test")
    username = factory.Sequence(lambda number: f"user{number}")
    first_name = factory.Faker("first_name")
    last_name = factory.Faker("last_name")
    status = AccountStatus.ACTIVE
    email_verified_at = factory.LazyFunction(timezone.now)
    password = factory.PostGenerationMethodCall("set_password", "A-very-secure-test-password-42")


class AdminUserFactory(UserFactory):
    is_staff = True
    is_superuser = True


class PermissionFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Permission

    codename = factory.Sequence(lambda number: f"resource{number}.view")
    description = factory.Faker("sentence")


class RoleFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Role

    name = factory.Sequence(lambda number: f"Role {number}")
    slug = factory.Sequence(lambda number: f"role-{number}")
    description = factory.Faker("sentence")
    priority = 100
