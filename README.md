# Django Foundation

A production-oriented, reusable Django 5.2 LTS foundation for Python 3.13+. It provides identity, security, authorization, APIs, background work, observability, storage, tests, and deployment infrastructure without project-specific business logic.

The repository favors explicit services and database constraints over signals and implicit behavior. Optional capabilities have their own app or settings boundary. Domain apps can be added without changing authentication or authorization internals.

## Features

- UUID custom user model, case-insensitive email/username uniqueness, profiles, preferences, account states, and timed/permanent bans
- Session and rotating JWT authentication, email verification, password reset, email/username changes, deactivation, and pseudonymous deletion
- Device/session inventory and revocation, escalating login protection with a database fallback and optional Redis acceleration, TOTP 2FA, and single-use recovery codes
- Permission-first RBAC with roles, time-bounded assignments, and explicit per-user `ALLOW`/`DENY` overrides
- Append-oriented structured audit records and separate user-visible security events
- In-app/email notifications, hashed scoped API keys, idempotency primitives, feature flags, runtime settings, secure files, and optional signed webhooks
- Versioned DRF API, stable errors, bounded pagination/filtering, request IDs, OpenAPI, health endpoints, JSON production logs, and optional Sentry
- SQLite or PostgreSQL, opt-in Redis/Celery/Beat/S3, Mailpit, Docker Compose, pytest, Ruff, and pre-commit

See [Architecture](docs/ARCHITECTURE.md), [API](docs/API.md), [Security](docs/SECURITY.md), and [Customization](docs/CUSTOMIZATION.md).

## AI-assisted development

This repository includes a canonical AI development contract in [AGENTS.md](AGENTS.md), focused module-level instructions, current context under [docs/ai](docs/ai/PROJECT_CONTEXT.md), and durable decisions under [docs/adr](docs/adr/README.md). Human and AI contributors should read the root instructions before architectural or security-sensitive changes. Tool-specific compatibility files only point to that canonical source and do not maintain duplicate rule sets.

## Requirements and supported modes

Only Python 3.13+ and pip are required for the minimal mode. [uv](https://docs.astral.sh/uv/) is supported for faster dependency management, and Docker 24+/Compose v2 is optional.

| Mode | Components | Install |
| --- | --- | --- |
| Minimal | Django + SQLite; no Redis or Celery | `pip install -e .` |
| Standard | Django + PostgreSQL; Redis/Celery not required | `pip install -e ".[postgres]"` |
| Advanced | Django + PostgreSQL + Redis + Celery + Beat | `pip install -e ".[postgres,redis,celery]"` |

Select the modes with `DATABASE_ENGINE`, `REDIS_ENABLED`, and `CELERY_ENABLED`; application code does not change. S3 and production server/observability dependencies are separate `s3` and `production` extras. SQLite is fully supported for local work and smaller deployments, while PostgreSQL is recommended for production concurrency, operations, and scale.

## Quick start: local

```bash
cp .env.example .env
python -m venv .venv
source .venv/bin/activate
python -m pip install -e .
python manage.py migrate
python manage.py bootstrap
python manage.py createsuperuser
python manage.py runserver
```

On Windows PowerShell, activate with `.venv\Scripts\Activate.ps1`. The checked-in example selects SQLite, disables Redis/Celery, and prints email to the console. A Redis URL may remain present while `REDIS_ENABLED=false`; it is not contacted. For development tools, use `pip install -e ".[dev]"` or `uv sync --extra dev`.

The API is at `http://localhost:8000/api/v1/`, admin at `/admin/`, Swagger at `/api/docs/`, and health at `/health/`.

## Quick start: Docker

```bash
cp .env.example .env
docker compose up -d --build
docker compose exec web python manage.py migrate
docker compose exec web python manage.py bootstrap
docker compose exec web python manage.py createsuperuser
```

Compose starts `web`, PostgreSQL, Redis, a Celery worker, Celery Beat, and Mailpit. Mailpit SMTP is port `1025`; its UI is [http://localhost:8025](http://localhost:8025). Migrations are intentionally explicit and never run automatically at container startup.

The Compose files describe the advanced mode. Docker validation is intentionally a separate Linux deployment check; the Python validation workflow does not require Docker.

## Environment configuration

`.env.example` documents every supported value. Important groups:

| Area | Variables |
| --- | --- |
| Runtime | `APP_ENV`, `DJANGO_SETTINGS_MODULE`, `DEBUG`, `SECRET_KEY`, `ALLOWED_HOSTS` |
| Branding | `APP_NAME`, `SITE_NAME`, `SITE_URL`, `SUPPORT_EMAIL`, `DEFAULT_FROM_EMAIL` |
| Data | `DATABASE_ENGINE`, `SQLITE_PATH`, `DATABASE_URL`, `DB_*`, `REDIS_ENABLED`, `REDIS_URL` |
| Email | `EMAIL_BACKEND`, `EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`, TLS/SSL flags |
| Browser | `CORS_ALLOWED_ORIGINS`, `CSRF_TRUSTED_ORIGINS`, `TRUST_PROXY_HEADERS`, `TRUSTED_PROXY_IPS` |
| Crypto | `TOTP_ENCRYPTION_KEY`, `API_KEY_PEPPER`, JWT lifetime variables |
| Workers | `CELERY_ENABLED`, `CELERY_BROKER_URL`, `CELERY_RESULT_BACKEND` |
| Storage | `STORAGE_BACKEND` and `AWS_*` S3-compatible settings |
| Optional | `ENABLE_NOTIFICATIONS`, `ENABLE_API_KEYS`, `ENABLE_TWO_FACTOR`, `ENABLE_WEBHOOKS`, `ENABLE_SENTRY`, OpenAPI flags |
| Retention | session, token, notification, audit, file, and webhook day values |

Generate independent production values, for example:

```bash
python -c "import secrets; print(secrets.token_urlsafe(64))"
```

Never reuse `SECRET_KEY`, `TOTP_ENCRYPTION_KEY`, or `API_KEY_PEPPER`. Secrets belong in the environment or a deployment secret manager, never in the runtime `Setting` table.

## PostgreSQL

Use SQLite with `DATABASE_ENGINE=sqlite` and `SQLITE_PATH=db.sqlite3`. Use PostgreSQL with `DATABASE_ENGINE=postgresql`, install the `postgres` extra, and either set a URL such as `DATABASE_URL=postgresql://user:password@host:5432/database` or set `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, and `DB_PORT`. Database selection is centralized in `config/settings/database.py`.

The portable schema uses functional uniqueness, temporal constraints, JSON fields, and targeted indexes supported by both databases. PostgreSQL is recommended in production and must be exercised for PostgreSQL-specific concurrency behavior before release. Run migrations from one controlled release job:

```bash
uv run python manage.py migrate --plan
uv run python manage.py migrate
```

## Redis

Redis is disabled by default. With `REDIS_ENABLED=false`, Django uses `LocMemCache`, sessions remain database-backed, and critical login protection stores hashed identifier/IP counters in the application database. General DRF throttles use the local Django cache in this mode and are therefore process-local; use a gateway limit or Redis for coordinated multi-process API throttling.

With `REDIS_ENABLED=true` and the `redis` extra installed, the Django cache and login protection use Redis. A configured URL is never contacted while the switch is false. When Redis is enabled, loss of the service is visible and security-sensitive operations do not silently downgrade to local memory.

## Celery and Celery Beat

```bash
celery -A config.celery worker --loglevel=INFO
celery -A config.celery beat --loglevel=INFO
```

Celery is disabled by default and is not imported at Django startup. Safe task dispatch runs synchronously when disabled, including email and enabled webhook delivery; failures remain visible to the request/service caller. Enable it with `CELERY_ENABLED=true`, install the `celery` extra, and configure a broker. A Redis broker also requires `REDIS_ENABLED=true` and the `redis` extra; another Celery-supported broker may be used instead.

Beat schedules session/token/notification/file/login-counter cleanup, optional audit retention, ban synchronization, and webhook dispatch. Without Beat, run the equivalent management commands from the platform scheduler. Retention is environment-driven; `AUDIT_RETENTION_DAYS=0` retains audit data indefinitely.

## Users and administrators

```bash
uv run python manage.py createsuperuser
uv run python manage.py bootstrap
uv run python manage.py seed --demo-admin  # development only; prints a random one-time password
```

`bootstrap` idempotently creates the permission registry, Super Admin/Admin/Moderator/User roles, the registration setting, and a base feature flag. It updates known definitions and never deletes unknown permissions.

## Authentication API

The primary routes are:

- `POST /api/v1/auth/register/`, `login/`, `logout/`, `token/refresh/`
- `POST /api/v1/auth/verify-email/`, `resend-verification/`
- `POST /api/v1/auth/password-reset/`, `password-reset/confirm/`, `password/change/`
- `POST /api/v1/auth/email/change/`, `email/change/confirm/`, `username/change/`
- `POST /api/v1/auth/account/deactivate/`, `account/delete/`, `account/delete/confirm/`
- `GET /api/v1/users/me/`; `GET/PATCH /users/me/profile/` and `/preferences/`

Login accepts email or username and creates both a secure Django session and a short-lived JWT access/rotating refresh pair. Browser clients should use sessions plus CSRF; external clients should use `Authorization: Bearer <access>`. Refresh tokens rotate and are blacklisted on use; account-wide security changes revoke outstanding refresh tokens. Access tokens remain intentionally short-lived.

Password-reset and verification requests return enumeration-safe responses. One-time tokens are hashed, expire, invalidate older tokens of the same purpose, and are consumed under a row lock.

## Two-factor authentication

TOTP works with standard authenticator apps. Setup requires password reauthentication:

1. `POST /api/v1/auth/2fa/setup/` with `password`; capture the secret/provisioning URI.
2. `POST /api/v1/auth/2fa/confirm/` with a current TOTP code.
3. Store the returned recovery codes; each is shown once and usable once.

Disable requires password plus TOTP/recovery code. Recovery-code regeneration requires a current TOTP/recovery code. Secrets are encrypted at rest and never placed in logs/admin; recovery codes are keyed hashes. Set `ENABLE_TWO_FACTOR=false` to return feature-disabled responses without changing core authentication.

## Sessions and devices

`/api/v1/users/me/sessions/` lists browser, OS, device type, IP, optional provider-supplied location, first login, activity, current/revoked state. Actions revoke one, all others, or all. The model stores a keyed hash plus encrypted session reference—not a directly usable plaintext secret. Revocation deletes Django’s server-side session and creates security/audit records.

## Roles and permissions

Authorization is based on codenames such as `users.view`; role names are never used in application decisions. Resolution order is:

1. deny unavailable/inactive/banned accounts;
2. explicit user `DENY`;
3. explicit user `ALLOW`;
4. Django superuser grant;
5. active time-bounded role permissions;
6. deny by default.

`DENY` therefore overrides roles and superuser access inside this custom permission system. Use `HasPermission` for global checks and `IsOwnerOrHasPermission` for explicit owner-or-global object checks. Views must declare querysets and ownership fields; client-supplied ownership/role fields are never trusted.

## Audit logs and security events

Audit rows carry actor, action, target, structured before/after/metadata, request ID, IP, user agent, and timestamp. Application updates/deletes are blocked; the only deletion path is explicit configured retention. Use database permissions/WORM export for stronger regulatory immutability.

Security events are a separate history for login, credential, 2FA, session, lock, account, and API-key activity. Users see only their history at `/users/me/security-events/`; authorized administrators use `/security-events/`. Admin writes to sensitive models are audited.

## Notifications

Notifications support in-app and email channels behind `NotificationService`. Users can list, mark one/all read, and delete only their own notifications at `/api/v1/notifications/`. `ENABLE_NOTIFICATIONS=false` removes the routes and prevents in-app creation. Push/webhook adapters can implement the same message interface later.

## API keys

`/api/v1/api-keys/` creates, lists, and revokes keys. The full `dk_<prefix>.<secret>` value is returned only on creation; storage contains a prefix and keyed hash. API-key authentication uses `X-API-Key` and is denied by default unless a view declares required scopes. Built-in scopes are configured with `API_KEY_AVAILABLE_SCOPES`. API keys cannot call security-sensitive endpoints or mint more keys.

## Files and storage

Application code uses Django’s storage API and `FileService`, never filesystem paths. `STORAGE_BACKEND=local` uses local media; `s3` uses `django-storages` for AWS S3, MinIO, Cloudflare R2, or another compatible endpoint.

`SecureFileValidator` enforces an explicit extension/MIME allowlist, maximum bytes, magic-byte detection, image verification/dimensions, randomized storage names, SHA-256 checksums, and an optional malware scanner callback. Define allowlists at each upload use case and add quota/scan hooks before marking content available.

## Runtime settings and feature flags

`Setting` stores typed, non-secret runtime values grouped by key; secret-like keys are rejected. `RuntimeSettingService` caches reads and invalidates on service writes. `FeatureFlag` provides global switches with room for a future targeting adapter. These core records are manageable through admin and permission-protected APIs.

## Idempotency and webhooks

Apply `@idempotent()` only to suitable authenticated state-changing view methods. It hashes `Idempotency-Key`, binds it to method/path/body/user, serializes completed JSON responses, and rejects conflicting reuse.

The optional webhook foundation stores endpoints/events/deliveries, encrypts signing material, signs timestamped HMAC-SHA256 payloads, rejects non-global destinations, disables redirects, truncates response bodies, retries with backoff, and recovers stale deliveries. Re-resolve/egress-filter destinations at the network layer too; DNS controls are part of SSRF defense.

## OpenAPI

`drf-spectacular` serves `/api/schema/`, `/api/docs/`, and `/api/redoc/` in development. Generate and validate a deployable schema with:

```bash
uv run python manage.py spectacular --file schema.yml --validate
```

Production docs are off unless `ENABLE_OPENAPI_IN_PRODUCTION=true`. Authentication schemes, pagination, stable errors, API keys, and rate-limit behavior are described in [docs/API.md](docs/API.md).

## Internationalization and branding

English and Turkish are configured; backend-facing labels use Django translation primitives where appropriate, timestamps are UTC, and each user has language/timezone preferences. Generate Turkish catalogs with `django-admin makemessages -l tr`.

Branding comes from `APP_NAME`, `SITE_NAME`, `SITE_URL`, `SUPPORT_EMAIL`, and `DEFAULT_FROM_EMAIL`. Email HTML/text templates share `templates/emails/base.html`; replace its visual treatment and static logo without changing services.

## Tests and code quality

```bash
uv run pytest
uv run ruff check .
uv run ruff format --check .
uv run pre-commit run --all-files
uv run python manage.py check
uv run python manage.py makemigrations --check --dry-run
```

Tests use pytest-django and factory-boy. Factories live in `tests/factories.py`; no large fixture JSON is required. The suite covers identity constraints, registration, login/logout, resets, permissions/overrides, states/bans, sessions, 2FA/recovery, API keys/scopes, lockouts, audit immutability, notifications, health, files, idempotency, and error envelopes.

## Commands

Common `make` targets: `install`, `dev`, `test`, `test-cov`, `lint`, `format`, `check`, `migrate`, `makemigrations`, `shell`, `superuser`, `bootstrap`, `seed`, `collectstatic`, `worker`, `beat`, `schema`, `docker-up`, `docker-down`, and `docker-logs`.

Management commands include `bootstrap`, `seed`, `healthcheck`, `cleanup_sessions`, `cleanup_tokens`, `cleanup_notifications`, `cleanup_login_attempts`, and `cleanup_audit`. Cleanup commands are idempotent with respect to eligible rows and obey configured retention.

## Production deployment

1. Build the multi-stage image and scan it.
2. Supply secrets through the platform secret manager; select `config.settings.production`.
3. Choose SQLite or preferably PostgreSQL; provision Redis, workers, and object storage only when enabled; configure SMTP/provider email.
4. Run `check --deploy`, migrations, `bootstrap`, and `collectstatic` as controlled release jobs.
5. Run the web process. If Celery is enabled, run worker and exactly one Beat scheduler as separate processes.
6. Route `/health/live/` and `/health/ready/` to orchestrator probes.
7. Terminate HTTPS at a trusted proxy, block direct application access, then enable forwarded headers with an explicit proxy IP allowlist.
8. Configure log collection, Sentry if desired, backups, retention, key rotation, and alerts.

The container runs as a non-root user and does not auto-migrate. See [docs/SECURITY.md](docs/SECURITY.md) for proxy, cookie, CORS/CSRF, CSP, and incident guidance.

## Extending the boilerplate

Create domain apps under `apps/` so imports stay namespaced:

```bash
mkdir apps/example
uv run python manage.py startapp example apps/example
```

Add `apps.example` to `LOCAL_APPS`, keep mutations in `services.py`, reads in `selectors.py`, HTTP adaptation in the API package, and tests under `tests/example/`. Register permissions from the app’s `AppConfig.ready()`:

```python
from apps.authorization.registry import register_permissions

register_permissions(
    {
        "example.view": "View example records",
        "example.create": "Create example records",
        "example.update": "Update example records",
        "example.delete": "Delete example records",
    }
)
```

Run `python manage.py bootstrap`; missing permissions are created and unknown permissions are preserved. Attach permissions to roles through bootstrap extensions, admin, or the RBAC API. Never branch business logic on role slugs.

## Replacing or disabling optional infrastructure

- Celery: leave `CELERY_ENABLED=false`; task dispatch and email execute synchronously. Do not run worker/Beat. Enable it by installing `.[celery]` and configuring a broker.
- Notifications/API keys/2FA/webhooks: set the matching `ENABLE_*` flag. Routes/services fail closed or are omitted. For physical removal, also remove the app, migration ownership, admin/API import, authentication class or schedule string listed in [Customization](docs/CUSTOMIZATION.md).
- Sentry: remains inactive unless both `ENABLE_SENTRY=true` and `SENTRY_DSN` are set.
- S3: keep local storage or replace the `STORAGES["default"]` backend; callers remain unchanged.
- JWT: session authentication is independent. Remove SimpleJWT routes/authentication/blacklist app only after migrating external clients.
- Redis: leave `REDIS_ENABLED=false` for local cache plus database-backed login protection. For multi-process coordinated DRF throttles/cache, enable Redis or enforce equivalent limits at a trusted gateway.

## Security considerations

Use HTTPS, rotate all installation-specific secrets, enforce least privilege, protect the admin with 2FA/network controls, restrict proxy ingress, validate every object queryset by tenant/owner, and monitor security/audit events. Do not add ownership, role, or permission fields to writable serializers without explicit authorization. Do not accept arbitrary filter/order fields. Do not log request bodies or headers.

Report vulnerabilities using the process in [docs/SECURITY.md](docs/SECURITY.md), not a public issue containing exploit details.

## License and changelog

Licensed under MIT; see [LICENSE](LICENSE). Changes are recorded in [CHANGELOG.md](CHANGELOG.md).
