# Customization Guide

## Reuse checklist

1. Clone the repository and create a new history/remote if this is a new product.
2. Keep `AUTH_USER_MODEL = "accounts.User"`; changing it after migrations is intentionally difficult.
3. Set branding (`APP_NAME`, `SITE_NAME`, `SITE_URL`, support/from email) and replace email visual assets/text.
4. Generate independent secrets and configure the development environment.
5. Choose SQLite or PostgreSQL, then opt into Redis, Celery, email, and storage providers as needed.
6. Select optional modules and remove only those the project will not need.
7. Create domain apps under `apps/` with services/selectors/API boundaries.
8. Register domain permissions and run `bootstrap`.
9. Add domain API routes below `/api/v1/`, serializers, object authorization, audit/events, and tests.
10. Configure production ingress, secrets, observability, backups, retention, and CI/CD.
11. Run all validation and a domain-specific threat review before launch.

## Rename and branding

The Python configuration package is intentionally neutral (`config`) and usually need not be renamed. The distribution name `django-foundation` in `pyproject.toml`, Celery app label, Compose project name, README/changelog, and deployment service names can be renamed without touching Django models.

Do not rename an app label after migrations without an explicit database migration plan. In particular, preserve `accounts.User` from project inception.

Branding lives in environment settings and the shared email base. Avoid replacing neutral strings in migration files. Add a logo through static files/storage and a context processor setting; do not hardcode absolute product URLs in services.

## Module classification

Required core:

- `config`, `common`, `apps.accounts`, `apps.authentication`, `apps.authorization`, `apps.security`, `apps.core`
- Django auth/contenttypes/sessions and DRF
- SQLite or PostgreSQL

Recommended:

- `apps.audit` for traceability
- `apps.api` for versioned DRF projects
- PostgreSQL for production concurrency and operational scale
- Redis/Celery for distributed cache/throttles, non-blocking email, and scheduled cleanup

Optional/removable:

- `apps.notifications`
- `apps.api_keys`
- `apps.files` and S3 extras
- `apps.webhooks`
- TOTP endpoints/models within authentication (runtime-disable unless making a custom migration)
- SimpleJWT for session-only deployments
- Sentry, OpenAPI production exposure, Celery runtime workers
- Redis and its cache backend
- Feature flags if the project does not need runtime rollout (part of `core`, so removal is a small code/data migration)

Runtime disabling is safer than deleting migration history and supports later activation. Remove physically only before deployment or through normal forward migrations.

## Create a domain app

```bash
mkdir apps/example
python manage.py startapp example apps/example
```

Add `"apps.example"` to `LOCAL_APPS`. A typical layout:

```text
apps/example/
├── admin.py
├── apps.py
├── models.py
├── services.py
├── selectors.py
├── tasks.py
├── permissions.py
├── migrations/
└── api/
    ├── serializers.py
    ├── views.py
    └── urls.py
tests/example/
```

Keep state changes in services:

```python
@transaction.atomic
def create_example(*, actor, name: str) -> Example:
    obj = Example.objects.create(name=name, owner=actor)
    AuditService.record(action="example.created", actor=actor, target=obj)
    transaction.on_commit(
        lambda: EventBus.publish(
            ApplicationEvent(
                name="example.created",
                actor_id=str(actor.pk),
                target_type="example.example",
                target_id=str(obj.pk),
            )
        )
    )
    return obj
```

Views should validate, authorize, call the service/selector, and serialize. Do not copy authentication, request-ID, email, storage, or exception behavior into the app.

## Register permissions

In `apps/example/apps.py`:

```python
from django.apps import AppConfig


class ExampleConfig(AppConfig):
    name = "apps.example"

    def ready(self):
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

`ready()` registers definitions in memory only; it does not write during startup. Run `python manage.py bootstrap` during deployment to add/update rows. Extend the bootstrap role definitions or manage role links explicitly. Unknown database permissions are never automatically deleted; deprecate, remove assignments, observe, then delete manually through an approved migration/process.

On views:

```python
class ExampleViewSet(ModelViewSet):
    permission_classes = [HasPermission, HasAPIKeyScope]

    @property
    def required_permission(self):
        return {"list": "example.view", "create": "example.create"}.get(
            self.action, "example.update"
        )
```

If API keys are allowed, declare exact `required_api_key_scopes` and add those strings to `API_KEY_AVAILABLE_SCOPES`. Omitting a declaration denies API keys by design.

## Object ownership

Global permission and object access are separate. Start with a constrained selector:

```python
def examples_visible_to(*, user):
    if PermissionService.has_permission(user, "example.view_all"):
        return Example.objects.all()
    return Example.objects.filter(owner=user)
```

Use it for list and detail querysets, then apply `IsOwnerOrHasPermission` when needed. Never accept `owner`, `tenant`, `created_by`, role, or permission from a generic writable serializer. Set those server-side from the authenticated context.

## Add background work

Put task definitions in the owning app and pass IDs/primitive data. Re-fetch and verify current state inside the task. Expose a domain service method that chooses synchronous/queued behavior rather than calling `.delay()` from every view. Add Beat entries to settings only for genuine schedules and make destructive retention configurable/off by default.

For durable once-only external side effects, add an outbox record in the same transaction. Celery delivery is at least once; idempotency belongs in the operation.

## Add email and notifications

Add both `.html` and `.txt` below `templates/emails/`, extending `base.html`. Call `EmailService.enqueue` inside `transaction.on_commit`. Never pass ORM objects to Celery manually; the service converts supported context to JSON-safe values.

Use `NotificationService` for in-app/email channel composition. Add push/webhook providers as channel adapters; do not embed provider SDK calls in domain services.

## Add file uploads

Define per-use-case allowed extensions/MIME types, byte/dimension limits, quota and scanner callbacks. Call `FileService.store`; store the returned model/ID, not a local path. For private content, configure private object storage and generate authorized signed downloads. Add owner-scoped APIs and scan-status rules before exposing files.

## Add idempotent operations

Apply `@idempotent(ttl=...)` to an authenticated JSON DRF method only after deciding:

- which authenticated principal owns the key;
- how long replay must be retained;
- whether the response is safe to store;
- how concurrent work is represented;
- how downstream external effects are deduplicated.

The generic primitive is a starting point, not a payment ledger.

## Disable or remove optional modules

### Notifications

Set `ENABLE_NOTIFICATIONS=false` to omit routes/prevent in-app creation. For physical removal, remove `apps.notifications`, its `LOCAL_APPS` entry, API view/import/route, Beat cleanup entry, admin, tests, and create a forward migration only if removing deployed tables.

### API keys

Set `ENABLE_API_KEYS=false`. For removal, delete the authentication class and global scope permission from `REST_FRAMEWORK`, remove app/API/admin/tests and the setting. Confirm all integrations have migrated first.

### Webhooks

Keep `ENABLE_WEBHOOKS=false` (default). For removal, delete app/admin/tasks, Beat entries, dependency `httpx` if no other caller uses it, and deployed tables via a reviewed forward migration.

### Files/S3

Remove the files app only if no model references it. S3 support is a production extra; local storage requires no boto dependency at runtime if the extra is omitted. Replace `STORAGES` without changing callers.

### Celery

Leave `CELERY_ENABLED=false`; the task adapter and email service run synchronously and Django never imports Celery. Stop worker/Beat and omit the `celery` extra. To enable it, install `.[celery]`, configure `CELERY_BROKER_URL`, and set `CELERY_ENABLED=true`. A Redis broker also requires `REDIS_ENABLED=true` plus `.[redis]`. Ensure synchronous web-request latency and email failure behavior are acceptable when workers are disabled.

### Redis

Leave `REDIS_ENABLED=false` to use `LocMemCache` plus database-backed login throttle records. The configured URL is ignored and no Redis connection is attempted. General DRF cache throttles are process-local in this mode; multi-process deployments need trusted gateway limits or Redis. To enable the shared cache, install `.[redis]`, set `REDIS_ENABLED=true`, and configure `REDIS_URL`.

### JWT

Remove `StatusAwareJWTAuthentication`, refresh/logout token handling, SimpleJWT/blacklist apps/dependency, and token cleanup only after external clients move to another scheme. Session/CSRF remains independent.

### TOTP

Set `ENABLE_TWO_FACTOR=false` to disable endpoints. Physical removal requires a forward migration for credentials/recovery codes and changes to login; consider retaining data during a reversible sunset window.

### Sentry/OpenAPI

Sentry imports only when enabled and configured. Remove its production extra if unused. Production OpenAPI exposure is independently controlled; schema generation can remain in CI even when public routes are off.

## Replace infrastructure

- Email: configure any Django email backend or replace `EmailService` internals while preserving its call signature/templates.
- Tasks: replace `enqueue`/domain dispatch boundaries with another queue; keep on-commit behavior and JSON-safe messages.
- Cache/login state: the default database fallback protects login across processes. Redis adds coordinated cache/DRF throttle state; an alternative shared backend must provide atomic increment and TTL semantics and fail visibly when enabled.
- Storage: configure any Django storage implementation.
- Observability: replace JSON log shipping/Sentry without logging request bodies or secrets.
- Permission engine: keep codenames/service interface while replacing persistence/resolution; migration must preserve deny precedence and account gate.

## Production customization review

Run:

```bash
python manage.py check --deploy --settings=config.settings.production
python manage.py makemigrations --check --dry-run
python manage.py migrate
python manage.py bootstrap
python manage.py spectacular --file schema.yml --validate
pytest
ruff check .
ruff format --check .
```

The Python checks above apply to every mode. Docker build/Compose startup are separate Linux validation steps. When a feature is selected, test actual PostgreSQL constraints/concurrency, Redis failure, worker/Beat startup, SMTP delivery into a safe inbox, S3 upload/download, proxy scheme/client IP, CORS/CSRF frontend flow, readiness under dependency loss, backups/restores, and domain-specific authorization abuse cases.
