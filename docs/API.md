# API Guide

## Conventions

The API root is `/api/v1/`. JSON is the default request/response format. Timestamps are ISO 8601 UTC values and identifiers are UUID strings. Collection filtering/search/ordering is opt-in per endpoint:

```text
?page=1&page_size=25&search=term&ordering=-created_at
```

`page_size` is capped at 100. Unsupported filters/order fields are not exposed. All responses include `X-Request-ID`; a valid incoming value containing 1–64 alphanumeric/`._:-` characters is preserved, otherwise generated.

## Authentication

Browser clients use Django’s `sessionid` cookie and submit `X-CSRFToken` on unsafe requests. Obtain the CSRF cookie through the frontend’s normal Django integration; never disable CSRF.

External clients use:

```http
Authorization: Bearer <access-token>
```

Refresh at `POST /api/v1/auth/token/refresh/`. API keys use:

```http
X-API-Key: dk_ab12cd34ef56.<secret>
```

API keys are accepted only on routes declaring matching scopes. They are not a substitute for session/JWT on account security, RBAC, audit, settings, session, or key-management endpoints.

## Response envelopes

Successful object/action responses:

```json
{
  "success": true,
  "data": {"id": "..."},
  "meta": {},
  "error": null
}
```

Paginated responses place the result array in `data` and provide `page`, `page_size`, `pages`, `count`, `next`, and `previous` under `meta.pagination`.

Errors:

```json
{
  "success": false,
  "data": null,
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Validation failed.",
    "fields": {"email": ["This field is required."]},
    "request_id": "4d72..."
  }
}
```

Stable codes include `VALIDATION_ERROR`, `AUTHENTICATION_REQUIRED`, `AUTHENTICATION_FAILED`, `PERMISSION_DENIED`, `RESOURCE_NOT_FOUND`, `CONFLICT`, `RATE_LIMITED`, `ACCOUNT_LOCKED`, `ACCOUNT_BANNED`, `TWO_FACTOR_REQUIRED`, `INVALID_TOKEN`, `FEATURE_DISABLED`, and `INTERNAL_ERROR`. Production internal errors contain no trace/details.

DRF’s schema/media responses may follow their required standard rather than an application envelope.

## Register and verify

```http
POST /api/v1/auth/register/
Content-Type: application/json

{
  "email": "person@example.com",
  "username": "person",
  "password": "a long unique passphrase",
  "first_name": "Example",
  "last_name": "Person"
}
```

The account begins `pending`. Submit the emailed token:

```http
POST /api/v1/auth/verify-email/

{"token": "single-use-token"}
```

Resend with `POST /api/v1/auth/resend-verification/` and `{"email":"..."}`. The response does not disclose eligibility.

## Login, refresh, and logout

```http
POST /api/v1/auth/login/

{
  "identifier": "person@example.com",
  "password": "a long unique passphrase",
  "remember_me": true,
  "code": "123456"
}
```

`code` is omitted unless 2FA is enabled; a recovery code can be supplied. Success returns `user`, `access`, `refresh`, and `session_id`. The session cookie expires at browser close unless `remember_me` selects the configured 30-day behavior.

```http
POST /api/v1/auth/token/refresh/
{"refresh":"..."}

POST /api/v1/auth/logout/
Authorization: Bearer <access>
{"refresh":"..."}
```

Logout blacklists the refresh and revokes the current Django session if present. Clients should immediately discard both tokens.

## Password and identity

- `POST /auth/password-reset/` — `email`; uniform response
- `POST /auth/password-reset/confirm/` — `token`, `new_password`
- `POST /auth/password/change/` — authenticated; `old_password`, `new_password`
- `POST /auth/email/change/` — authenticated; `password`, `new_email`
- `POST /auth/email/change/confirm/` — `token`
- `POST /auth/username/change/` — authenticated; `username`
- `POST /auth/account/deactivate/` — authenticated; `password`
- `POST /auth/account/delete/` — authenticated; `password`, then email confirmation
- `POST /auth/account/delete/confirm/` — `token`

Password reset/change revokes other sessions and outstanding refresh tokens. Email change verifies the new address and revokes other credentials. Deletion pseudonymizes the core identity/profile and publishes an extension event; domain apps must attach their approved retention/deletion behavior.

## Two-factor authentication

```http
POST /api/v1/auth/2fa/setup/
{"password":"current password"}
```

The response contains a secret and provisioning URI; display/store it only during setup. Confirm with `POST /auth/2fa/confirm/` and `{"code":"123456"}`. The returned recovery codes are shown once.

Disable with `/auth/2fa/disable/` (`password`, `code`). Regenerate recovery codes with `/auth/2fa/recovery-codes/regenerate/` (`code`). Security events and notification emails accompany enable/disable/recovery use.

## Current user and sessions

- `GET /users/me/`
- `GET|PUT|PATCH /users/me/profile/`
- `GET|PUT|PATCH /users/me/preferences/`
- `GET /users/me/security-events/`
- `GET /users/me/sessions/`
- `POST /users/me/sessions/{identifier}/revoke/`
- `POST /users/me/sessions/revoke-others/`
- `POST /users/me/sessions/revoke-all/`

Profile read/write API-key scopes are `profile.read` and `profile.write`. API keys are intentionally denied on sessions/security history.

## Notifications

- `GET /notifications/`
- `GET /notifications/{id}/`
- `POST /notifications/{id}/read/`
- `POST /notifications/read-all/`
- `DELETE /notifications/{id}/`

Every queryset is current-user scoped. API keys need `notifications.read`; deployments can split the built-in scope or add a write scope requirement when customizing actions.

## API keys

Create via authenticated session/JWT, optionally idempotently:

```http
POST /api/v1/api-keys/
Idempotency-Key: integration-setup-2026-01

{
  "name": "Reporting integration",
  "scopes": ["profile.read", "notifications.read"],
  "expires_at": "2027-01-01T00:00:00Z"
}
```

The response alone includes `key`. `GET /api-keys/` and `GET /api-keys/{id}/` never return it. Revoke with `POST /api-keys/{id}/revoke/`. Configure allowed scopes in `API_KEY_AVAILABLE_SCOPES`; declaring a string does not grant an endpoint until that view also requires it.

## RBAC administration

Session/JWT users with `roles.manage` can use `/roles/`, `/permissions/`, `/role-permissions/`, `/user-roles/`, and `/permission-overrides/`. System roles/permissions cannot be deleted. Assignments accept optional validity times. Never expose these routes to API keys merely by adding broad scopes without a security review.

User administration at `/users/` requires action-specific `users.view/update/...`. Creation and deletion intentionally use dedicated account lifecycle services rather than generic model CRUD.

## Audit, security, settings, and flags

- `/audit-logs/` — read only; `audit.view`
- `/security-events/` — administrative read only; `security_events.view`
- `/settings/` — `settings.view`/`settings.update`
- `/feature-flags/` — `feature_flags.view`/`feature_flags.update`

Audit/security filters and ordering are allowlisted. Runtime settings reject secret-like keys. Public settings are not automatically anonymous endpoints; expose a narrow selector if a frontend needs them.

## Idempotency

Only endpoints decorated by their author honor `Idempotency-Key`; API-key creation is the built-in example. A key is scoped to the authenticated user and bound to method, path, and raw body. Exact replay returns the stored response with `Idempotent-Replayed: true`; different request reuse returns `409 CONFLICT`; concurrent in-progress reuse also returns conflict.

Do not apply idempotency to streaming, file, or non-JSON responses without extending storage behavior. Choose retention for business operations when adding them.

## Rate limits

Configured scopes include anonymous, authenticated, login, registration, password reset, verification resend, and API-key operations. A throttle response is `429` with `RATE_LIMITED`; DRF may include a retry duration. Login protection is additional stateful backoff by hashed identifier/IP dimensions and remains database-backed when Redis is disabled. General DRF throttles use the configured Django cache; without Redis they are process-local, so a multi-process deployment must add trusted gateway limits or another shared throttle backend.

## Schema and examples

OpenAPI endpoints are `/api/schema/`, `/api/docs/`, and `/api/redoc/` when enabled. Treat the generated schema as the field-level source of truth and this guide as lifecycle/security context. Validate schema in CI:

```bash
python manage.py spectacular --file schema.yml --validate
```
