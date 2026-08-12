# Development Rules for AI Agents

## Before implementing a feature

1. Read `/AGENTS.md`, relevant nested instructions, AI context, and applicable ADRs.
2. Search for models, services, routes, permissions, settings, tasks, templates, commands, and tests related to the request.
3. Trace at least one existing comparable flow from URL to service/model and tests.
4. Identify whether the request is foundation infrastructure or product-domain behavior. Put product behavior in a new domain app.
5. Reuse current abstractions; list any genuine gaps before adding a new one.
6. Identify authentication, authorization, ownership/IDOR, enumeration, concurrency, secret, logging, file, and external-call risks.
7. Define required dotted permissions and API-key scopes. Decide how querysets are constrained.
8. Identify schema changes, database constraints/indexes, data migration needs, and both SQLite/PostgreSQL behavior.
9. Identify optional-infrastructure behavior with Redis/Celery disabled.
10. Identify tests and documentation that will prove the change.

For non-trivial work, make a short implementation plan before editing.

## While implementing

- Make the smallest coherent change that fits established boundaries.
- Keep views/serializers thin and mutations transactional in services.
- Set ownership/actor fields server-side.
- Use `transaction.on_commit()` for work that must not run before a successful commit.
- Use existing centralized services for email, notifications, audit, security events, tasks, storage, responses, settings, flags, and idempotency.
- Add constraints for durable invariants; use application validation for helpful errors.
- Allowlist query/filter/order fields.
- Preserve error codes and enumeration-safe public messages.
- Keep optional imports lazy/isolated and minimal mode functional.
- Add tests alongside the implementation rather than postponing them.
- Do not make unrelated formatting or architecture changes.

## Adding a new domain feature

For a future feature such as `orders`:

1. create `apps/orders/` and `tests/orders/`;
2. add it to `LOCAL_APPS`;
3. define UUID models and database integrity rules;
4. put mutations in `services.py`;
5. put reusable/visibility-constrained reads in `selectors.py`;
6. register `orders.view/create/update/delete` or a justified narrower permission set;
7. add thin API serializers/views/routes under the versioned API;
8. use existing audit/notification/task/file infrastructure;
9. create and inspect migrations;
10. add unit, integration, permission, ownership, and regression tests.

Do not modify login, RBAC resolution, common responses, or core settings merely to attach a domain feature.

## Adding permissions

- Use stable dotted codenames based on capability, not UI labels or role names.
- Register them with `register_permissions()` from the owning app's `AppConfig.ready()`.
- Registration must only update the in-process registry; `bootstrap` performs database synchronization.
- Add role grants explicitly if defaults truly require them. Do not grant new capabilities to existing roles without reviewing privilege expansion.
- Add `HasPermission`/`required_permission` to administrative APIs and ownership rules separately.

## Adding APIs

- Prefer a dedicated service/selector before the HTTP adapter.
- Explicitly enumerate serializer fields and read-only fields.
- Declare permissions, API-key scopes, throttles, ordering/search/filter fields, and pagination behavior.
- Return established envelopes and stable errors.
- Update `apps/api/urls.py` or a domain URL module included beneath `/api/v1/`.
- Regenerate/validate `schema.yml` when the public contract changes.

## Adding background work

- Use `common.tasks.shared_task`, never `celery.shared_task` in app modules.
- A task accepts UUID/string/primitive context, not ORM objects or secrets.
- Re-fetch and revalidate current state.
- Make repeated delivery harmless or detect completed state.
- Dispatch through an owning service, normally after commit.
- Define synchronous behavior when `CELERY_ENABLED=false` and add a Beat entry only when scheduling is required.

## Adding configuration or dependencies

Use environment variables for secrets and deployment topology. Update `.env.example`, settings validation, README/config docs, and tests. Use runtime `Setting` only for non-secret mutable values and `FeatureFlag` for global booleans.

Before adding a package, prove it is needed, check existing dependencies, use the smallest maintained option, choose core versus an optional extra correctly, update `uv.lock`, and test a minimal install without the extra.

## After implementing

1. Run targeted tests while iterating, then the full relevant suite.
2. Run Django checks and migration consistency checks.
3. Apply migrations on SQLite; use a fresh database when schema changed.
4. Run Ruff lint and format checks.
5. Validate OpenAPI for API changes.
6. Review permission, ownership, API-key scope, and negative paths manually.
7. Review concurrency, idempotency, retries, and transaction/on-commit behavior.
8. Check backward compatibility and optional-infrastructure disabled behavior.
9. Search for dead code, duplicate abstractions, unfinished markers, secret leakage, and inaccurate docs.
10. Update normal docs, AI context, project state, or ADRs only when their architectural/current-state statements changed.

Do not create an AI-specific changelog. `CHANGELOG.md` remains version history.
