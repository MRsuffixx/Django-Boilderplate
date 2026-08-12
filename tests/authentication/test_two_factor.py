import pyotp
import pytest
from django.test import RequestFactory

from apps.authentication.models import RecoveryCode
from apps.authentication.services import TwoFactorService


pytestmark = pytest.mark.django_db


def test_two_factor_setup_encrypts_secret_and_returns_single_use_recovery_codes(user):
    secret, uri = TwoFactorService.begin_setup(user=user)
    credential = user.two_factor
    assert secret not in credential.encrypted_secret
    assert uri.startswith("otpauth://totp/")

    codes = TwoFactorService.confirm_setup(user=user, code=pyotp.TOTP(secret).now())

    credential.refresh_from_db()
    assert credential.is_enabled
    assert len(codes) == TwoFactorService.recovery_code_count
    assert RecoveryCode.objects.filter(credential=credential, used_at__isnull=True).count() == len(codes)

    valid, recovery_used = TwoFactorService.verify(user=user, code=codes[0])
    assert valid and recovery_used
    valid_again, _ = TwoFactorService.verify(user=user, code=codes[0])
    assert not valid_again


def test_two_factor_can_be_disabled_with_password_and_totp(user):
    secret, _ = TwoFactorService.begin_setup(user=user)
    TwoFactorService.confirm_setup(user=user, code=pyotp.TOTP(secret).now())

    TwoFactorService.disable(
        user=user,
        password="A-very-secure-test-password-42",
        code=pyotp.TOTP(secret).now(),
        request=RequestFactory().post("/"),
    )

    user.two_factor.refresh_from_db()
    assert not user.two_factor.is_enabled
