from __future__ import annotations

import pytest
from django.db import IntegrityError, transaction

from apps.accounts.models import AccountStatus, User

pytestmark = pytest.mark.django_db


def test_create_user_normalizes_entire_email_and_uses_uuid():
    user = User.objects.create_user(
        email="  PERSON@Example.COM ",
        username="person",
        password="A-very-secure-password-42",
    )

    assert user.email == "person@example.com"
    assert user.status == AccountStatus.PENDING
    assert user.check_password("A-very-secure-password-42")
    assert user.pk.version == 4


def test_case_insensitive_email_constraint():
    User.objects.create_user(email="person@example.test", username="person1", password="password")

    with pytest.raises(IntegrityError), transaction.atomic():
        User.objects.create_user(
            email="PERSON@example.test", username="person2", password="password"
        )


def test_case_insensitive_username_constraint():
    User.objects.create_user(email="one@example.test", username="Person", password="password")

    with pytest.raises(IntegrityError), transaction.atomic():
        User.objects.create_user(email="two@example.test", username="person", password="password")


def test_superuser_has_required_state():
    user = User.objects.create_superuser(
        email="admin@example.test",
        username="admin",
        password="A-very-secure-password-42",
    )

    assert user.is_superuser
    assert user.is_staff
    assert user.status == AccountStatus.ACTIVE
    assert user.is_email_verified
