# Redis is optional infrastructure

## Status

Accepted

## Context

Redis is valuable for shared caching, coordinated API throttles, Celery brokers/backends, and high-volume temporary state. Requiring it prevents a developer from cloning and running the reusable foundation with only Python and SQLite. Simply falling back to process-local security counters would weaken brute-force protection in multi-process deployments.

## Decision

Gate Redis with `REDIS_ENABLED`, defaulting to false. While disabled:

- use Django `LocMemCache` for ordinary cache/DRF throttle state;
- keep Django sessions database-backed;
- store hashed login identifier/IP/composite counters in `LoginThrottleState` through `LoginProtectionService`;
- do not import a Redis client, select the Redis cache backend, or attempt a connection.

While enabled, select `django-redis` through settings and use Redis for cache/login protection. Require the `redis` dependency extra and a configured URL. Do not silently downgrade an enabled Redis-backed security feature after service failure.

## Consequences

- Minimal and standard modes have no Redis installation/runtime requirement.
- Critical login brute-force state remains shared through the application database.
- General DRF throttles are process-local without Redis; multi-process deployments need Redis or trusted gateway enforcement.
- Redis-dependent additions must define disabled behavior and avoid module-level client initialization.
- Enabled Redis becomes monitored security-sensitive infrastructure and its unavailability is visible.
