from rest_framework.throttling import ScopedRateThrottle


class LoginThrottle(ScopedRateThrottle):
    scope = "login"


class RegisterThrottle(ScopedRateThrottle):
    scope = "register"


class PasswordResetThrottle(ScopedRateThrottle):
    scope = "password_reset"


class EmailVerificationThrottle(ScopedRateThrottle):
    scope = "email_verification"


class APIKeyThrottle(ScopedRateThrottle):
    scope = "api_key"
