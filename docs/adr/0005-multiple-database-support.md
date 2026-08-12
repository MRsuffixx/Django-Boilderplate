# SQLite and PostgreSQL are supported

## Status

Accepted

## Context

The foundation must be immediately usable without provisioning a database service while still supporting a production database with robust concurrency and operational tooling. Scattered environment-specific database logic and PostgreSQL-only ORM features would make these modes diverge.

## Decision

Support SQLite and PostgreSQL in core functionality. Centralize selection in `config/settings/database.py` through `DATABASE_ENGINE`:

- SQLite uses `SQLITE_PATH` and is the local default.
- PostgreSQL accepts `DATABASE_URL` or explicit `DB_*` variables and requires the optional `postgres` driver extra.

Use portable model fields, constraints, and ORM queries in core code. A PostgreSQL-specific feature must have an equivalent SQLite fallback or be explicitly isolated/documented as PostgreSQL-only.

## Consequences

- A clone can migrate and run with no external database service.
- Production deployments are encouraged to choose PostgreSQL for concurrency, backups, observability, and scale.
- SQLite CI/testing catches portability errors but cannot validate PostgreSQL row-lock/concurrency behavior.
- JSON lookups, raw SQL, indexes, and constraints require backend-compatibility review.
- Database selection logic must not be duplicated in environment settings modules.
- Security/concurrency-sensitive releases should add real PostgreSQL integration validation when infrastructure is available.
