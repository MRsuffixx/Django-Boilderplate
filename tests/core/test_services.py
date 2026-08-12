from datetime import timedelta

import pytest
from django.core.exceptions import ValidationError
from django.utils import timezone

from apps.audit.models import AuditLog
from apps.audit.services import AuditService
from apps.audit.tasks import cleanup_audit_logs
from apps.core.models import FeatureFlag, Setting, SettingValueType
from apps.core.services import FeatureFlagService, RuntimeSettingService

pytestmark = pytest.mark.django_db


def test_runtime_setting_service_validates_types_and_rejects_secrets():
    row = RuntimeSettingService.set(
        key="site.registration_enabled",
        value=False,
        value_type=SettingValueType.BOOLEAN,
        is_public=True,
    )
    assert RuntimeSettingService.get(row.key, True) is False

    with pytest.raises(ValidationError):
        RuntimeSettingService.set(
            key="smtp.password",
            value="must-not-be-stored",
            value_type=SettingValueType.STRING,
        )
    assert not Setting.objects.filter(key="smtp.password").exists()


def test_feature_flag_service_preserves_explicit_false():
    FeatureFlag.objects.create(key="feature.example", enabled=False)
    assert FeatureFlagService.is_enabled("feature.example", default=True) is False
    assert FeatureFlagService.is_enabled("feature.missing", default=True) is True


def test_audit_retention_is_disabled_by_default_and_explicit_when_enabled(user, settings):
    log = AuditService.record(action="retention.test", target=user)
    settings.AUDIT_RETENTION_DAYS = 0
    assert cleanup_audit_logs() == 0

    # auto_now_add is adjusted with SQL through a migration-safe update path unavailable by design;
    # create an old timestamp through a direct model insert override for the retention test.
    AuditLog.objects.filter(pk=log.pk)._update(
        [
            (
                AuditLog._meta.get_field("created_at"),
                None,
                timezone.now() - timedelta(days=10),
            )
        ]
    )
    settings.AUDIT_RETENTION_DAYS = 1
    assert cleanup_audit_logs() == 1
    assert not AuditLog.objects.filter(pk=log.pk).exists()
