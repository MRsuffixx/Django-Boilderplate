from datetime import timedelta

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone

from apps.accounts.models import AccountStatus
from apps.accounts.tasks import expire_temporary_bans
from apps.authentication.models import OneTimeToken, TokenPurpose, UserSession
from apps.authentication.tasks import cleanup_sessions, cleanup_tokens
from apps.files.models import FileStatus, StoredFile
from apps.files.tasks import cleanup_unused_files
from apps.notifications.models import Notification
from apps.notifications.tasks import cleanup_notifications
from apps.security.models import LoginThrottleState
from apps.security.tasks import cleanup_login_attempts
from common.tasks import shared_task

pytestmark = pytest.mark.django_db


def test_scheduled_ban_synchronization_activates_due_ban(user):
    user.bans.create(
        reason="Scheduled",
        starts_at=timezone.now() - timedelta(minutes=1),
        expires_at=timezone.now() + timedelta(hours=1),
    )

    assert expire_temporary_bans() == 1
    user.refresh_from_db()
    assert user.status == AccountStatus.BANNED


def test_session_and_token_cleanup_respect_retention(user, settings):
    settings.SESSION_RETENTION_DAYS = 30
    settings.TOKEN_RETENTION_DAYS = 7
    session = UserSession.objects.create(
        user=user,
        identifier="a" * 32,
        session_key_hash="b" * 64,
        encrypted_session_key="encrypted",
        revoked_at=timezone.now() - timedelta(days=31),
    )
    token = OneTimeToken.objects.create(
        user=user,
        purpose=TokenPurpose.PASSWORD_RESET,
        token_hash="c" * 64,
        expires_at=timezone.now() - timedelta(days=8),
    )

    assert cleanup_sessions() >= 1
    assert cleanup_tokens() >= 1
    assert not UserSession.objects.filter(pk=session.pk).exists()
    assert not OneTimeToken.objects.filter(pk=token.pk).exists()


def test_notification_and_file_cleanup_are_policy_driven(user, settings):
    settings.NOTIFICATION_RETENTION_DAYS = 30
    settings.FILE_RETENTION_DAYS = 7
    notification = Notification.objects.create(
        user=user,
        type="old",
        title="Old",
        message="Expired",
        read_at=timezone.now() - timedelta(days=31),
    )
    Notification.objects.filter(pk=notification.pk).update(
        created_at=timezone.now() - timedelta(days=31)
    )
    stored = StoredFile.objects.create(
        owner=user,
        file=SimpleUploadedFile("pending.bin", b"pending"),
        original_name="pending.bin",
        content_type="application/octet-stream",
        size=7,
        checksum_sha256="d" * 64,
        status=FileStatus.PENDING,
    )
    StoredFile.objects.filter(pk=stored.pk).update(created_at=timezone.now() - timedelta(days=8))

    assert cleanup_notifications() >= 1
    assert cleanup_unused_files() == 1
    stored.refresh_from_db()
    assert not Notification.objects.filter(pk=notification.pk).exists()
    assert stored.deleted_at is not None


def test_expired_login_throttle_cleanup():
    state = LoginThrottleState.objects.create(
        dimension_hash="e" * 64,
        expires_at=timezone.now() - timedelta(seconds=1),
    )

    assert cleanup_login_attempts() == 1
    assert not LoginThrottleState.objects.filter(pk=state.pk).exists()


def test_task_dispatch_runs_synchronously_without_celery(settings):
    settings.CELERY_ENABLED = False

    @shared_task(name="tests.synchronous_task")
    def add(left, right):
        return left + right

    assert add.delay(2, 3) == 5
    assert add.apply_async(args=(4, 5)) == 9
