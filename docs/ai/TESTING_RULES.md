# Testing Rules for AI Agents

## Organization and tools

- Tests use pytest, pytest-django, and factory-boy.
- Put tests in `tests/<owning_app>/test_<behavior>.py`.
- Shared factories are in `tests/factories.py`; add focused factories there when broadly reusable.
- Prefer factory composition and small fixtures over committed JSON fixture dumps.
- Test service behavior directly and add API integration tests where HTTP/auth/envelope behavior matters.
- A confirmed bug requires a failing regression test before or with the fix.

## Required test types

### Model and service tests

Cover normalization, constraints, state transitions, transactions, idempotency, cleanup retention, and failure behavior. Do not only assert model creation.

### API tests

Cover success envelope, stable error code, validation fields, request ID, pagination/query allowlists, and schema when relevant.

### Permission and ownership tests

For a permissioned endpoint, test as applicable:

- anonymous/no credential;
- authenticated without permission;
- explicit deny despite role/superuser;
- active valid role or explicit allow;
- expired/future assignment;
- owner accessing own object;
- authenticated user accessing another user's valid UUID;
- API key without, with wrong, and with correct scope.

### Security regressions

Credential/recovery/session/2FA/API-key/file changes need replay, reuse, enumeration, bypass, secret-exposure, and concurrent-state tests where applicable. Assert raw secrets do not appear in persistence or normal serialized output.

### Optional infrastructure

Default tests run with SQLite, `REDIS_ENABLED=false`, and `CELERY_ENABLED=false`. New infrastructure-dependent features must test their disabled path. Task code should remain callable normally and synchronous `.delay()` behavior should be tested when the fallback matters.

Mock boundaries, not the logic under test. Do not make unit tests depend on a live Redis/Celery broker/email/S3 service unless explicitly running an integration profile.

## Database and migration validation

SQLite compatibility is mandatory for core functionality. Avoid assertions that accidentally depend on PostgreSQL-only ordering/JSON behavior. When a change involves locking, functional constraints, query plans, or backend-specific operations, also describe/run PostgreSQL integration validation when available.

For schema changes:

1. generate and inspect the migration;
2. run `makemigrations --check`;
3. migrate an existing local database;
4. migrate a fresh SQLite database from zero;
5. test data migrations both forward behavior and idempotency where relevant;
6. never edit prior migration history solely to make the check pass.

## Default validation commands

```bash
python manage.py check
python manage.py makemigrations --check
python manage.py migrate
pytest
ruff check .
ruff format --check .
```

Also run:

```bash
python manage.py spectacular --file schema.yml --validate
```

when API routes/serializers/schema/authentication documentation changes. Run `pre-commit run --all-files` for final repository-wide delivery when practical.

Docker and Docker Compose are intentionally excluded from normal AI validation unless the user explicitly requests them. Docker files currently await manual validation on Linux. Do not block completion on Docker when it is out of scope.

## Completion evidence

Report the exact commands run, pass/fail counts, coverage result, database mode, and any external systems not exercised. Do not claim PostgreSQL/Redis/Celery/Docker were integration-tested when only settings or import smoke tests ran.
