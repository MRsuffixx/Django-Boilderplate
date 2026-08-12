# Current Project State

This is a lightweight current-state snapshot for new AI agents. It is not version history; use `CHANGELOG.md` for releases.

## Status

The reusable Django foundation is implemented and functional in its default zero-infrastructure configuration. It is structured for product-domain apps to be added without replacing identity, authentication, RBAC, API, audit, notification, storage, or observability infrastructure.

## Implemented systems

- UUID custom user, case-insensitive email/username constraints, profile/preferences/security settings, account states, temporary/permanent bans.
- Registration, verification, login/logout, rotating JWT refresh, password reset/change, email/username change, deactivation, pseudonymous deletion.
- Database-backed Django sessions with user-visible device inventory/revocation.
- TOTP 2FA, encrypted secrets, single-use hashed recovery codes.
- Permission-first RBAC, system roles, time-bounded assignments, explicit allow/deny overrides, object-level helper.
- Escalating login brute-force protection, persistent account locks, security event history.
- Append-oriented audit logs, request IDs, structured/redacted logging, optional Sentry.
- In-app/email notifications, centralized templates/email service.
- Hashed scoped API keys with one-time raw display.
- Runtime settings, feature flags, API idempotency primitive.
- Secure file validation/storage abstraction and optional S3 backend.
- Optional signed outbound webhook foundation with SSRF controls/retries.
- Versioned DRF API, standardized errors/success responses, bounded pagination, filter/search/order conventions, OpenAPI.
- Health/liveness/readiness endpoints, management bootstrap/seed/cleanup commands.
- pytest/factory-boy suite, Ruff, pre-commit, Docker/Docker Compose files, and developer/security/API/customization documentation.

## Infrastructure support

- SQLite: supported and the default local database.
- PostgreSQL: supported through `DATABASE_ENGINE=postgresql` and the `postgres` extra; recommended for production.
- Redis: optional. Disabled mode uses LocMem cache and database-backed login counters. No Redis connection is attempted while disabled.
- Celery/Beat: optional. Disabled mode uses synchronous task dispatch. Celery is not imported by Django startup while disabled.
- Docker: files exist for an advanced PostgreSQL/Redis/Celery/Mailpit development stack, but validation is intentionally deferred to manual Linux testing.
- Local minimum: the project must run with Django + SQLite and no Redis, Celery, Docker, PostgreSQL, or S3.

## Current automated validation baseline

The latest repository review validated minimal-mode Django startup, checks, migrations (including fresh SQLite), bootstrap, OpenAPI generation, Ruff, pre-commit, and the full pytest suite. Optional PostgreSQL/Redis/Celery settings and Celery task registration received a no-connection smoke test; this is not a live service integration test.

## Known limitations and deliberate boundaries

- LocMem-backed general DRF throttles are per process without Redis. Multi-process deployments need Redis or trusted gateway limits. Critical login protection still uses shared database state.
- SQLite does not reproduce PostgreSQL row-lock/concurrency behavior. Production-sensitive concurrency should be integration-tested on PostgreSQL.
- `EventBus` is synchronous and non-durable. It is not an outbox/message broker.
- WebAuthn/passkeys are an extension point, not currently implemented.
- Runtime feature flags are global only; targeted rollout is an extension point.
- Audit immutability is application-level. Strong regulatory immutability requires database privileges and/or external WORM/SIEM export.

## Pending manual/external validation

- Docker image build and Docker Compose startup on Linux.
- Real PostgreSQL migrations, constraints, locking, and concurrency behavior.
- Real Redis cache/throttle behavior and enabled-service failure response.
- Real Celery worker and Beat processing with the selected broker/backend.
- Mailpit/SMTP delivery, production provider integration, S3-compatible storage, and reverse-proxy behavior as selected by a deployment.

## Durable decisions

Read `docs/adr/` before changing the custom user model, UUID identity, service layer, optional Redis/Celery boundaries, or dual-database support.
