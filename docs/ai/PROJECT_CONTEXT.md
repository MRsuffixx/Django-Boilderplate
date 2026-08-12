# Project Context for AI Agents

## Purpose and philosophy

Django Foundation is a reusable Django 5.2 LTS boilerplate for Python 3.13+. It is designed to become the infrastructure base for unrelated future products. It intentionally contains no product-domain models such as orders, products, payments, or stores.

The project favors explicit services, database constraints, permission-first authorization, environment-driven configuration, secure defaults, and replaceable optional infrastructure. Start small without external services, then enable production components without changing application code.

Read `/AGENTS.md` before modifying the repository. This document is a quick orientation, not a replacement for its rules.

## Technology stack

Core dependencies:

- Django 5.2 LTS and Django REST Framework;
- SimpleJWT with refresh rotation and blacklist support;
- drf-spectacular, django-filter, django-cors-headers, django-environ;
- Argon2 password hashing, cryptography/Fernet, pyotp;
- Pillow/filetype for secure upload inspection;
- httpx for outbound webhooks;
- python-json-logger and WhiteNoise.

Development dependencies are under the `dev` extra. PostgreSQL, Redis, Celery, S3, and production server/observability packages are separate optional extras in `pyproject.toml`.

## Supported infrastructure modes

| Mode | Database | Cache/login throttles | Task dispatch |
| --- | --- | --- | --- |
| Minimal | SQLite | LocMem + database login counters | synchronous |
| Standard | PostgreSQL | LocMem + database login counters | synchronous |
| Advanced | PostgreSQL | Redis | Celery + Beat |

`DATABASE_ENGINE`, `REDIS_ENABLED`, and `CELERY_ENABLED` select the mode. Minimal mode must work without installing Redis, Celery, psycopg, Docker, or S3 packages.

SQLite and PostgreSQL are both supported by core functionality. PostgreSQL is recommended for production concurrency and operational scale. General DRF cache throttles are process-local without Redis; critical login throttling remains shared through the database.

## Major modules and models

- `accounts`: UUID `User`, `UserProfile`, `UserPreferences`, `UserSecuritySettings`, `UserBan`, and account states.
- `authentication`: `OneTimeToken`, `UserSession`, `TwoFactorCredential`, `RecoveryCode`; session/JWT/TOTP/account lifecycle services.
- `authorization`: `Permission`, `Role`, `RolePermission`, `UserRole`, `UserPermissionOverride`; additive registry and resolver.
- `security`: `SecurityEvent`, `LoginThrottleState`; brute-force and user security history.
- `audit`: append-oriented `AuditLog` and centralized `AuditService`.
- `core`: typed runtime `Setting`, global `FeatureFlag`, `IdempotencyRecord`, health endpoints, bootstrap/cleanup commands.
- `notifications`: user-scoped `Notification` plus in-app/email composition.
- `api_keys`: owner-scoped hashed API keys, one-time raw display, configured scopes.
- `files`: `StoredFile`, secure validators, Django storage abstraction, cleanup.
- `webhooks`: endpoint/event/delivery records, encrypted signing material, SSRF checks, HMAC signing, retry tasks.
- `api`: all `/api/v1/` transport adapters; no durable domain logic.
- `common`: shared middleware, error/response conventions, pagination, permissions, email, tasks, events, logging, crypto, base models.

## Authentication flow

Registration creates a pending account and sends a hashed one-time verification token. Verification activates the account. Login accepts email or username and:

1. checks hashed identifier/IP brute-force state;
2. authenticates the password;
3. checks account state, active bans, persistent lock, and verification lifecycle;
4. verifies TOTP/recovery code when enabled;
5. creates a Django session plus short-lived JWT access/rotating refresh tokens;
6. records the tracked device session and security/audit events.

Password/email/account security changes revoke applicable sessions and outstanding refresh tokens. Browser clients use session cookies and CSRF. External clients use JWT. API keys use `X-API-Key` only on endpoints declaring scopes.

Secrets are protected as follows: passwords through Django hashing; one-time tokens/API keys/recovery codes through keyed hashes; TOTP and tracked session references through purpose-separated encryption.

## Authorization flow

`PermissionService` first denies unavailable accounts. Explicit user `DENY` overrides explicit `ALLOW`, superuser, and roles. Otherwise explicit `ALLOW`, superuser, then active time-bounded role permissions grant access; default is deny.

Roles are collections, not authorization predicates. Object visibility is separately constrained in querysets/selectors. API-key scopes are an additional fail-closed layer, not a replacement for user permission/ownership rules.

The permission registry is in `apps/authorization/registry.py`. `bootstrap` additively synchronizes it and creates the default Super Admin, Admin, Moderator, and User roles.

## API structure

- Root application API: `/api/v1/`.
- Authentication lifecycle: `/api/v1/auth/`.
- Current user/profile/preferences/sessions/security history: `/api/v1/users/me/`.
- Administrative resources: users, roles, permissions, assignments/overrides, audit, security events, settings, flags.
- Optional routes: notifications and API keys.
- OpenAPI: `/api/schema/`, `/api/docs/`, `/api/redoc/` when enabled.

Success actions use the `success/data/meta/error` envelope; exceptions are normalized by the centralized DRF exception handler with stable codes and request IDs. Pagination is page-number based with a maximum page size of 100.

## Configuration system

`config/settings/base.py` contains shared settings. Development, production, and test modules override environment behavior. `config/settings/database.py` is the single database builder. `.env.example` is the configuration inventory.

Deployment topology and secrets belong in environment variables. Mutable, non-secret product configuration uses `Setting` through `RuntimeSettingService`; simple global rollouts use `FeatureFlagService`. Sentry activates only when configured. Django storage switches between local and the optional S3 backend.

## Extension points

- Add product domains as new apps under `apps/`, with their own models/services/selectors/tasks/API/tests.
- Register dotted permissions through `register_permissions()`.
- Extend `/api/v1/` with thin DRF adapters.
- Use `common.tasks.shared_task` for optional background execution.
- Use `EmailService`, `NotificationService`, `AuditService`, `SecurityEventService`, and `FileService` rather than provider calls.
- Use `EventBus` only for non-critical synchronous extension hooks; introduce an explicit outbox if durable events become necessary.
- Apply `@idempotent()` only to deliberately chosen authenticated JSON operations.

For present validation and limitations, read `PROJECT_STATE.md`. For why durable choices exist, read the ADRs.
