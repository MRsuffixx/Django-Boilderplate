# Explicit service layer for state changes

## Status

Accepted

## Context

Authentication, role assignment, bans, API keys, sessions, files, notifications, and webhooks can be invoked from APIs, admin, commands, tasks, or future interfaces. Putting workflows in views, serializers, model hooks, or signals would duplicate logic, obscure transaction boundaries, and make security behavior inconsistent.

## Decision

Use explicit owning-app services for state changes and cross-model rules. Views/serializers remain HTTP validation/adaptation layers. Reusable or complex reads use selectors or constrained querysets. Services own transactions, row locks, audit/security records, and required side effects; dispatch side effects after commit where appropriate.

Use the small `EventBus` only for non-critical synchronous extension hooks. Avoid signals for critical behavior. Tasks are execution adapters and must re-fetch current state rather than contain the sole definition of a business rule.

## Consequences

- Mutations have one reusable boundary across HTTP/admin/commands/tasks.
- Tests can target services independently from API transport.
- Service methods need explicit actor/request context for audit and authorization-sensitive behavior.
- Simple CRUD may look slightly more verbose, but security and transactions remain visible.
- Future domain apps should add `services.py` and introduce `selectors.py` when reads become reusable/complex rather than building logic in API classes.
- A durable distributed event requirement would need a separate outbox decision; the current `EventBus` is not durable.
