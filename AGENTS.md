# AI Agent Instructions

> **Read this file before making architectural or significant code changes.**

Before making significant changes:

1. Read this file completely.
2. Inspect every existing file related to the request.
3. Read the relevant documents under `docs/ai/` and applicable ADRs under `docs/adr/`.
4. Understand and reuse existing abstractions before introducing new ones.
5. Never assume a feature is missing until you search the repository.
6. Prefer extending the existing system over creating a parallel implementation.

Nested `AGENTS.md` files add rules for their directory tree. They supplement, and never replace, this root contract.

## Repository purpose

This repository is a reusable, production-oriented Django boilerplate and application foundation, not a product-specific application. It supplies identity, authentication, authorization, security, APIs, audit, notifications, files, background-work boundaries, configuration, testing, and deployment scaffolding. New products should add domain apps without rewriting these systems.

Preserve these invariants:

- no project-specific business logic in boilerplate infrastructure;
- secure, explicit service boundaries;
- both SQLite and PostgreSQL remain supported;
- Redis and Celery remain optional;
- minimal mode remains Django + SQLite, with no Redis, Celery, or Docker;
- optional modules fail closed or disable explicitly, never silently weaken security.

## Read next

- `docs/ai/PROJECT_CONTEXT.md` — concise system map and current implementation.
- `docs/ai/ARCHITECTURE_RULES.md` — dependency and responsibility boundaries.
- `docs/ai/DEVELOPMENT_RULES.md` — feature implementation rules.
- `docs/ai/SECURITY_RULES.md` — mandatory security contract.
- `docs/ai/TESTING_RULES.md` — tests and completion checks.
- `docs/ai/CHANGE_WORKFLOW.md` — required understand-to-document workflow.
- `docs/ai/PROJECT_STATE.md` — current capabilities and manual validation still pending.
- `docs/adr/` — reasons behind durable architectural decisions.

Developer-facing references remain authoritative for their subjects: `README.md`, `docs/ARCHITECTURE.md`, `docs/API.md`, `docs/SECURITY.md`, and `docs/CUSTOMIZATION.md`.

## Source map

| Path | Responsibility |
| --- | --- |
| `config/` | URL composition, ASGI/WSGI, optional Celery app, split environment settings |
| `config/settings/database.py` | The only database-selection builder |
| `common/` | Cross-cutting models, middleware, API errors/responses, tasks, events, logging, permissions, email |
| `apps/accounts/` | Custom user, profiles, preferences, account security settings, account states, bans |
| `apps/authentication/` | Login, sessions, one-time tokens, JWT revocation, account lifecycle, TOTP and recovery codes |
| `apps/authorization/` | Permission registry, RBAC models, assignments, overrides, resolution |
| `apps/security/` | Security events and login brute-force protection |
| `apps/audit/` | Append-oriented structured audit records |
| `apps/api/` | Versioned DRF serializers, views, throttles, URLs, and schema adapters |
| `apps/core/` | Runtime settings, feature flags, idempotency records, health, shared tasks and commands |
| `apps/notifications/` | In-app notification records and email-channel composition |
| `apps/api_keys/` | Hashed scoped API keys and DRF authentication |
| `apps/files/` | Storage metadata, secure validation, and cleanup hooks |
| `apps/webhooks/` | Optional signed outbound webhook foundation |
| `templates/emails/` | Paired HTML/text centralized email templates |
| `tests/` | pytest suite, arranged by application; shared factories in `tests/factories.py` |

## Architectural flow

Normal write flow:

```text
URL / DRF view
    -> serializer input validation
    -> authentication + permission/scope checks
    -> transactional service
    -> model/ORM state change
    -> audit/security records and on-commit side effects
    -> standard response
```

Normal read flow:

```text
URL / DRF view
    -> authentication + permission/scope checks
    -> ownership-constrained queryset or reusable selector
    -> serializer
    -> paginated/standard response
```

- Views adapt HTTP only. Keep them thin.
- Serializers validate transport shape and field relationships. They do not orchestrate state transitions.
- Services own mutations, cross-model rules, transactions, row locks, audit/security records, and important side effects.
- Selectors own reusable or complex reads and must never write.
- Models own durable schema, local invariants, constraints, and small state-independent properties.
- Tasks re-fetch current data from primitive IDs; they do not trust stale authorization decisions.
- `EventBus` is only for non-critical in-process extension hooks. It is synchronous and non-durable.

Do not introduce hidden writes in selectors, critical behavior in signals, or network calls while holding database locks.

## Authentication architecture

`AUTH_USER_MODEL` is permanently `accounts.User`. It uses UUID identity and case-insensitive database constraints for email/username. Account eligibility is not just `is_active`; `User.can_authenticate_now()` requires active status and no active ban.

`apps.authentication.services` is the credential/lifecycle boundary:

- `AuthenticationService` handles login, lockout checks, 2FA verification, Django session creation, and login events.
- `AccountService` handles registration, verification, password reset/change, email/username changes, deactivation, and pseudonymous deletion.
- `TokenService` issues and consumes hashed, expiring, single-use tokens and revokes outstanding JWTs.
- `SessionService` registers/revokes tracked Django sessions.
- `TwoFactorService` owns encrypted TOTP secrets and single-use hashed recovery codes.

Browser clients use Django sessions plus CSRF. External/mobile clients use short-lived JWT access tokens with rotating, blacklisted refresh tokens. API keys are a separate scoped integration credential and are not an account-security credential.

Never add an authentication path that bypasses account state, active-ban, lockout, verification, 2FA, session, or token-revocation rules.

## Authorization and RBAC

Permissions—not role names—are the authorization contract. `PermissionService` resolves in this order:

1. account/authentication eligibility gate;
2. explicit user `DENY`;
3. explicit user `ALLOW`;
4. Django superuser grant;
5. active, time-bounded role permissions;
6. deny by default.

Do not branch business logic on role slugs such as `admin`. Do not trust client-provided roles, permissions, owner IDs, tenant IDs, or `created_by` values.

Global permission does not automatically grant object access. Constrain querysets by owner/tenant first, or use an explicit selector and `IsOwnerOrHasPermission` when a global permission may widen visibility. API-key access also requires explicit view scopes through `HasAPIKeyScope`; omitted scopes deny API keys by design.

Register new permission codenames through `apps.authorization.registry.register_permissions()`, then run `python manage.py bootstrap`. Bootstrap is additive and must not silently delete unknown permissions.

## API conventions

- All application routes live under `/api/v1/` in `apps/api/urls.py`.
- Use DRF serializers, views/viewsets, routers, and `drf-spectacular` annotations/extensions already present.
- Use `common.responses.success_response()` for standard successful actions and `StandardPagination` for collections.
- Let `common.exceptions.api_exception_handler` produce stable error envelopes and request IDs.
- Raise existing DRF exceptions or `common.exceptions.APIException` with a stable uppercase code.
- Declare `permission_classes`, `required_permission`, API-key scopes, throttle class, filter/search/order allowlists, and constrained querysets explicitly.
- Never expose unrestricted filter/order fields or writable ownership/security fields.
- Keep schema generation valid with `python manage.py spectacular --file schema.yml --validate` when API contracts change.

## Data and migration rules

- All application entities use UUID primary keys unless a Django/third-party table dictates otherwise.
- Use `UUIDModel`, `TimeStampedModel`, and explicit `SoftDeleteModel` only where their semantics fit.
- Prefer database constraints for durable integrity and targeted indexes for demonstrated query patterns.
- Core functionality must work on SQLite and PostgreSQL. Do not add PostgreSQL-only fields, lookups, SQL, or constraints without a compatible fallback or a clearly isolated PostgreSQL-only feature.
- Use `transaction.atomic()` and `select_for_update()` for security-sensitive races. Remember that SQLite does not reproduce PostgreSQL lock/concurrency behavior.
- Generate migrations with Django. Inspect generated operations. Never edit applied migration history casually, renumber migrations, or put data-dependent destructive behavior in startup.
- `makemigrations --check` must be clean. Fresh migrations must work from zero.
- Do not add soft deletion globally or make the default manager invisibly hide rows.

## Settings and environment

Settings are composed from `config/settings/base.py` plus `development.py`, `production.py`, or `test.py`. Database selection is centralized in `config/settings/database.py`; do not duplicate it in an environment file.

Environment values are documented in `.env.example`. Secrets stay in environment/secret managers, never in the runtime `Setting` table. `apps.core.models.Setting` is for typed non-secret runtime configuration; `FeatureFlag` is for lightweight global rollout switches.

Supported modes:

- Minimal: `DATABASE_ENGINE=sqlite`, `REDIS_ENABLED=false`, `CELERY_ENABLED=false`.
- Standard: `DATABASE_ENGINE=postgresql`, Redis/Celery still optional.
- Advanced: PostgreSQL + `REDIS_ENABLED=true` + `CELERY_ENABLED=true`.

### Optional Redis

Never assume Redis exists. With Redis disabled, Django uses `LocMemCache`, sessions use the database, and `LoginProtectionService` stores hashed throttle dimensions in `LoginThrottleState`. General DRF cache throttles are process-local in this mode.

Only enable Redis through `REDIS_ENABLED` and the `redis` dependency extra. Do not import a Redis client or contact Redis during startup in disabled mode. If an enabled Redis-backed security feature loses Redis, do not silently downgrade it to weaker process-local state.

### Optional Celery

Never import Celery directly from domain/application task modules. Import `shared_task` from `common.tasks`. It delegates to Celery when enabled and exposes synchronous `.delay()`/`.apply_async()` behavior when disabled.

Call background work through service/task boundaries, preferably in `transaction.on_commit()`. Pass JSON-safe primitives, re-fetch state, and design for at-least-once delivery. Celery Beat schedules belong in settings and destructive cleanup policies must remain configurable.

## Logging, audit, and events

- Use Python `logging`; do not add another logging framework.
- Request ID/user context comes from `common.context` and middleware.
- Production JSON formatting sanitizes keys matching password, authorization, cookie, token, secret, API key, session, TOTP, recovery-code, or encryption patterns.
- Never log request bodies, authentication headers, cookies, raw tokens, secrets, passwords, API keys, recovery codes, TOTP seeds, or encrypted session material.
- Use `AuditService` for privileged/state-changing action history and `SecurityEventService` for user-visible security history.
- Do not treat `EventBus` as a durable message bus or put critical integrity logic in handlers.

## Code style, naming, and dependency conventions

- Python 3.13+, Django 5.2 LTS, type hints on service/public utility boundaries where practical.
- Ruff owns formatting, imports, linting, and security rules. Line length is 100.
- Use clear domain names, `snake_case` functions/modules, `PascalCase` classes, and stable dotted permission names such as `orders.view`.
- Keep imports one-directional: domain apps may depend on infrastructure; infrastructure must not import future product apps.
- Avoid speculative abstraction and duplicate helpers. Search first.
- Avoid signals for critical flows; use explicit services and on-commit hooks.

Before adding a dependency:

1. prove the existing stack cannot reasonably solve the need;
2. check for an equivalent installed dependency;
3. choose a maintained, appropriately sized library;
4. add it to the correct `pyproject.toml` group/extra and refresh `uv.lock`;
5. add tests and document any infrastructure/configuration impact;
6. verify an optional dependency did not become mandatory in minimal mode.

## Testing and completion

Tests live under `tests/<app>/`; use factory-boy factories from `tests/factories.py` rather than large fixture dumps. Add regression tests for every confirmed bug. Security changes require negative/bypass tests, not only happy paths. Permissioned endpoints need unauthenticated, denied, allowed, ownership, and API-key-scope coverage as applicable.

Default validation:

```bash
python manage.py check
python manage.py makemigrations --check
python manage.py migrate
pytest
ruff check .
ruff format --check .
```

Run OpenAPI validation for API changes and fresh-database migrations for schema changes. Validate SQLite by default; validate PostgreSQL-specific concurrency/behavior when available.

Docker and Docker Compose are intentionally not mandatory AI completion checks unless the user explicitly asks for them. Current Docker validation is deferred to manual Linux testing.

## Extension recipes

### Add a product domain app

1. Create `apps/<domain>/` and add it to `LOCAL_APPS`.
2. Keep its models, services, selectors, tasks, API adapters, admin, migrations, and tests in that domain.
3. Register domain permissions.
4. Include domain URLs under `/api/v1/`.
5. Add audit/security/notification side effects only through existing services.
6. Do not modify authentication/core infrastructure merely because a domain app was added.

A future `orders` app, for example, owns order models/services/selectors/API/tests. It does not place order logic in `accounts`, `authentication`, `core`, or `common`.

### Add an API endpoint

1. Define/reuse a service or selector in the owning app.
2. Add an input/output serializer under `apps/api/serializers/` or a domain API package.
3. Add a thin view with explicit authentication, permission, scope, throttle, queryset, and query-field rules.
4. Register the route under `/api/v1/`.
5. Add API, authorization, ownership, error-envelope, and schema tests.

### Add a background task

1. Put it in the owning app's `tasks.py`.
2. Decorate with `common.tasks.shared_task`.
3. Pass primitive identifiers, re-fetch state, and make retries safe.
4. Dispatch behind a service boundary/on commit.
5. Test both normal function behavior and no-Celery synchronous dispatch when relevant.

### Add runtime configuration

Use environment settings for secrets, deployment topology, and startup-critical values. Use `Setting`/`RuntimeSettingService` only for non-secret, mutable product configuration. Use `FeatureFlagService` for simple global flags. Update `.env.example` and configuration docs for new environment values.

## Prevent architecture drift

Do not casually add another authentication framework, permission system, API envelope, settings store, event architecture, email abstraction, logging framework, task abstraction, cache abstraction, or file-storage abstraction. Inspect and extend the existing implementation first. If it is inadequate, document the deficiency and evolve or deliberately replace it; do not leave two competing systems.

## Never do this

- Add project-specific business logic to reusable core apps.
- Put substantial orchestration in views, serializers, admin actions, model `save()`, or signals.
- Bypass `PermissionService`, object ownership constraints, account gates, or API-key scopes.
- Trust client-supplied ownership, privilege, role, status, audit actor, or security metadata.
- Store or log plaintext passwords, raw API keys, refresh/one-time tokens, recovery codes, or TOTP secrets.
- Disable CSRF globally, enable wildcard production CORS, expose stack traces, or trust arbitrary proxy headers.
- Add unconditional Redis/Celery/PostgreSQL/S3 imports to minimal-mode code.
- Call a Celery task directly from unrelated views or call a Redis client directly from domain logic.
- Add PostgreSQL-only core behavior without a SQLite path.
- Use raw SQL when the ORM can safely express the operation.
- Edit old migrations to hide a new schema change or auto-run migrations at application startup.
- Create a second changelog for AI work. Update `CHANGELOG.md` for version history and AI context/ADRs only when architecture or current state actually changes.
