# Celery is optional infrastructure

## Status

Accepted

## Context

Queued email, webhook delivery, and scheduled cleanup are valuable for larger deployments, but a queue/broker/worker should not be required to start the foundation or experiment locally. Direct Celery imports and `.delay()` calls throughout application code would make the dependency mandatory and tightly couple domain behavior to one task runner.

## Decision

Gate Celery with `CELERY_ENABLED`, defaulting to false. Application task modules import `shared_task` from `common.tasks`, not Celery. The adapter uses Celery when enabled and provides synchronous function, `.delay()`, and `.apply_async()` execution when disabled.

Do not import `config.celery` from the root `config` package. Initialize it only when enabled or when a worker explicitly runs `celery -A config.celery`. Dispatch work through service/task boundaries, generally after transaction commit. Tasks accept JSON-safe primitives and re-fetch current state.

## Consequences

- Django starts and authentication/email/application flows work without Celery installed.
- Disabled task failures are visible synchronously and may increase request latency; callers must understand that tradeoff.
- Enabled deployments install the `celery` extra, configure a broker/backend, and run workers/one Beat scheduler.
- A Redis broker requires both Redis enablement and its optional dependency; another Celery-supported broker may be configured.
- Every new task must preserve synchronous disabled-mode behavior and at-least-once/retry safety.
- Scheduled cleanups need Beat or an external scheduler invoking the provided management commands.
