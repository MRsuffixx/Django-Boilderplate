# Common infrastructure instructions

Read `/AGENTS.md` first. Changes here affect nearly every app and require repository-wide impact review.

- `common` contains dependency-light cross-cutting primitives, not product/domain behavior.
- Extend existing response, exception, pagination, middleware, permission, email, event, task, crypto, model, logging, and network helpers before adding alternatives.
- `common.tasks.shared_task` is the only task decorator boundary; it preserves no-Celery operation.
- `EmailService` is the only templated email sending boundary. Add paired HTML/text templates and pass JSON-safe context for queued work.
- `EventBus` is synchronous, non-durable, and only for non-critical decoupled hooks.
- `SoftDeleteModel` deliberately does not hide rows in its default manager. Do not change this globally.
- Middleware must not log bodies or secrets and must preserve request-ID propagation.
- Crypto changes require a migration/key-rotation compatibility plan; do not invent cryptography.
- Avoid importing optional infrastructure at module load or importing product-domain apps into `common`.
