import pytest
from django.core.exceptions import ValidationError

from apps.audit.services import AuditService

pytestmark = pytest.mark.django_db


def test_audit_log_redacts_sensitive_fields_and_is_immutable(user):
    log = AuditService.record(
        action="user.updated",
        target=user,
        actor=user,
        after={"email": user.email, "password": "never-store-me", "access_token": "secret"},
    )

    assert log.after["password"] == "[REDACTED]"
    assert log.after["access_token"] == "[REDACTED]"
    log.action = "tampered"
    with pytest.raises(ValidationError):
        log.save()
    with pytest.raises(ValidationError):
        log.delete()
