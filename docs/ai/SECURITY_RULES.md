# Security Contract for AI Agents

Authentication, authorization, account recovery, email/password changes, 2FA, sessions, API keys, file uploads, webhooks, admin actions, and proxy/client-IP behavior are security-sensitive. Treat a small edit in these areas as a high-risk change.

## Absolute prohibitions

Never:

- store plaintext passwords;
- store raw API keys after their one-time display;
- store reusable one-time tokens or recovery codes in plaintext;
- log passwords, submitted 2FA/recovery codes, authorization headers, cookies, session keys, access/refresh tokens, API keys, TOTP secrets, encryption material, reset/verification tokens, or request bodies;
- add an authentication shortcut or bypass account state, bans, lockouts, verification, 2FA, session revocation, or JWT revocation;
- bypass `PermissionService`, API-key scopes, or ownership-constrained querysets;
- trust client-provided owner, tenant, actor, role, permission, status, `is_staff`, `is_superuser`, or audit/security metadata;
- enable wildcard production CORS or disable CSRF globally;
- expose Django/DRF stack traces or raw internal exceptions to clients;
- accept arbitrary redirects or unvalidated return URLs;
- commit secrets or use stable example secrets in real configuration;
- accept filenames, extensions, MIME declarations, image content, or storage paths as trustworthy;
- use raw SQL unnecessarily or build SQL from client strings;
- make authorization decisions only in frontend code;
- trust forwarded IP/protocol headers without the configured proxy boundary;
- silently disable a security control because Redis/Celery/external infrastructure is unavailable.

## Required patterns

### Credentials and recovery

Use Django password hashing and validators. One-time tokens are random, purpose-bound, keyed-hashed, expiring, superseding, and consumed atomically. Public reset/verification/resend responses must resist account enumeration. Credential changes revoke relevant sessions and refresh tokens and create audit/security records.

### Sessions, JWT, and API keys

Django sessions remain CSRF-protected and HttpOnly. JWT access tokens are short-lived; refresh tokens rotate and blacklist. Current account status and active bans are checked after token validation. Tracked sessions never expose the encrypted server-side reference.

API keys are generated with strong randomness, stored as prefix plus keyed hash, shown once, expire/revoke, and require exact view scopes. They are not allowed on account-security or privilege-management endpoints unless deliberately redesigned and reviewed.

### 2FA

TOTP setup requires password reauthentication and confirmation. Secrets remain encrypted and hidden from admin/logging. Recovery codes are shown once, keyed-hashed, row-locked, and single-use. Disable/regeneration must verify the current user and required credential.

### Authorization and IDOR

Authenticate first, check global permission, then constrain the queryset by owner/tenant or explicitly widen it through an audited permission-aware selector. Never fetch an arbitrary UUID and rely on serializer presentation to hide it. Test unauthorized users against valid object IDs.

### Files

Use `SecureFileValidator`/`FileService` and Django storage. Define explicit per-use-case extension/MIME/size/dimension allowlists, inspect magic bytes, randomize names, verify images, and provide scanner/quota hooks. Private files require authorized download behavior; storage location alone is not authorization.

### Webhooks and outbound requests

Preserve HTTPS requirements in production, URL credential rejection, DNS resolution checks against private/reserved addresses, redirect disabling, response truncation, HMAC signing, retry bounds, and network-level egress controls. Revalidation immediately before delivery is required because DNS can change.

### Transactions and concurrency

Use database constraints plus transactions/row locks for token/code consumption, credential changes, role/override changes, session/API-key revocation, and other security state. Never perform external network I/O while a database row lock is held.

### Logging and errors

Use existing structured logging and sanitizer. Log event names and safe IDs, not sensitive payloads. Include request IDs for correlation. Return stable generic errors; production internal errors contain no detail.

## Security review checklist

For every security-sensitive change, check:

- account enumeration and timing/message differences;
- privilege escalation and explicit-deny precedence;
- object-level bypass/IDOR;
- mass assignment;
- token/code replay and concurrent reuse;
- session fixation/revocation and refresh-token reuse;
- brute-force thresholds and no-Redis fallback;
- unsafe redirects, CORS, CSRF, proxy trust, and SSRF;
- secret/PII leakage in logs, audit metadata, emails, tasks, admin, schema, and responses;
- race conditions, transaction boundaries, task retries, and failure after commit;
- SQLite/PostgreSQL behavioral differences.

Add negative regression tests for the plausible attacks, not only successful behavior tests. Read `docs/SECURITY.md` for deployment controls.
