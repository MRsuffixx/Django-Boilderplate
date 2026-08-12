# Architecture Rules for AI Agents

These rules make the repository extensible without accumulating competing frameworks. Root authority is `/AGENTS.md`; nested `AGENTS.md` files add local constraints.

## Dependency direction

```text
API / admin / command / task adapter
              |
              v
       service or selector
              |
              v
          model / ORM
```

Cross-cutting side effects go through established infrastructure services:

```text
service -> AuditService / SecurityEventService
        -> EmailService / NotificationService
        -> common.tasks.shared_task (optional queue)
        -> EventBus (non-critical, in-process only)
```

Infrastructure must not import future product apps. A domain app may depend on stable accounts/authorization/audit/notification/file interfaces.

## Responsibility boundaries

### Views and API adapters

Views own HTTP concerns: authentication, permission declarations, API-key scopes, throttles, serializer invocation, queryset selection, status codes, and response formatting. They may not own multi-step account/domain state transitions.

### Serializers and validators

Serializers own request shape, parsing, allowlisting, and transport-specific validation. Reusable security/file validators may live with the owning infrastructure module. Do not put email sending, audit creation, role assignment, token issuance, or multi-model writes in serializer `create()`/`update()` when a service boundary exists.

### Services

Services own mutations and rules that must hold from HTTP, admin, tasks, commands, or future interfaces. They choose transaction boundaries, row locks, durable state, audit/security records, and on-commit side effects. Service APIs should accept explicit keyword arguments and authenticated actor/request context where relevant.

### Selectors and querysets

Selectors own reusable, meaningful reads. Simple constrained reads can stay in a view's `get_queryset()`. Use `select_related()`/`prefetch_related()` based on serializer access. A selector must never write, send messages, mutate caches, or change authorization state.

### Models

Models define schema, database constraints, targeted indexes, small local invariants, and state-independent properties. Avoid orchestration in `save()`; the existing `User.save()` normalization is a narrow exception. Do not add provider calls or cross-app workflows to models.

### Permissions

Global authorization belongs in `PermissionService` and DRF permission classes. Ownership/tenant visibility belongs in selectors/querysets before object retrieval. Role names are never authorization logic. Client data is never authority.

### Tasks

Tasks belong to the app owning the data. Decorate with `common.tasks.shared_task`, pass primitives, re-fetch records, re-check current state, and make retry behavior safe. Network I/O must occur outside database locks. A task is execution transport, not the only place a business rule exists.

### Events and signals

`EventBus` handlers are synchronous and errors are logged; they are suitable only for non-critical hooks. Critical security, integrity, and required side effects stay explicit in services. Avoid Django signals for critical workflows. If durability/ordering becomes required, design an outbox and record the decision in an ADR.

## Architecture-drift prohibitions

Do not introduce a second:

- authentication framework;
- RBAC/permission resolver;
- API success/error envelope;
- runtime settings/feature-flag system;
- task dispatch abstraction;
- email abstraction;
- event bus;
- logging stack;
- cache abstraction;
- file storage/upload abstraction.

If the current implementation cannot support a requirement, document the exact gap and evolve the existing boundary. A deliberate replacement needs migration, compatibility, tests, documentation, and usually an ADR.

## Optional-infrastructure boundary

Minimal mode is a non-negotiable architecture test. Code imported by Django startup cannot unconditionally import Redis, Celery, psycopg, boto/S3, or other optional clients.

- Redis selection occurs in settings. Login protection branches through `LoginProtectionService`.
- Celery selection occurs through `common.tasks.shared_task`; domain modules do not import Celery.
- PostgreSQL selection occurs only in `config/settings/database.py`.
- Storage selection occurs through Django `STORAGES` and `FileService`.

An optional feature must have defined disabled behavior, enabled configuration validation, and tests for the disabled path.

## Database portability

Core models and queries must run on SQLite and PostgreSQL. JSON containment and PostgreSQL-specific SQL are known portability traps; filter portably or isolate an optimized backend-specific path behind an equivalent fallback. Treat SQLite test success as portability coverage, not as proof of PostgreSQL locking semantics.

## Cross-cutting changes

Before changing `common/`, settings, authentication, authorization, account identity, middleware, response formats, base models, or permission resolution, search all consumers and run the full test suite. These are foundation contracts, not local implementation details.
