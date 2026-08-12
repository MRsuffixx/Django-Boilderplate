# Security Guide

## Reporting

Send vulnerability reports privately to the configured `SUPPORT_EMAIL` or the repository owner’s private security channel. Include affected version, reproduction, impact, and mitigation if known. Do not include live secrets or personal data. Establish acknowledgment and disclosure timelines for the organization using this boilerplate.

## Threat model and guarantees

The foundation defends common web/API risks through Django ORM escaping, template autoescaping, CSRF middleware, strict serializers, ownership-constrained querysets, permission checks, credential hashing/encryption, throttling, secure defaults, and redacted logging. It cannot compensate for an exposed database superuser, compromised host, unsafe domain app, untrusted reverse proxy, or missing network egress controls.

## Secrets

- Use independent random values for `SECRET_KEY`, `TOTP_ENCRYPTION_KEY`, and `API_KEY_PEPPER`.
- Store secrets in a platform secret manager/environment injection, not `.env` in deployed images and never the `Setting` table.
- Rotate with a planned migration. Rotating the TOTP encryption key without re-encrypting credentials makes existing secrets unreadable; rotating the API-key pepper invalidates all keys; rotating `SECRET_KEY` invalidates Django sessions/JWT signatures and other derived values.
- Prefer workload/IAM roles for S3 over static keys. If static keys are necessary, scope and rotate them.
- Never place credentials in URLs, task arguments visible to operators, analytics, Sentry tags, or logs.

Production startup validates critical settings and minimum key lengths. It requires PostgreSQL, Redis, an HTTPS `SITE_URL`, explicit allowed hosts, and a delivery-capable email backend.

## Authentication protections

- Passwords use Argon2 first and Django’s standard validators with a 12-character minimum.
- Login accepts email/username but returns a uniform invalid-credential message.
- Redis tracks hashed identifier, IP, and combined dimensions with escalating temporary backoff. Account locks are persisted only for identifier-based failures, avoiding global-IP lockout amplification.
- Correct-password login still checks account state, active bans, persistent lock, email lifecycle state, and TOTP.
- One-time tokens are random, keyed-hashed, expiring, superseding, and row-locked on use.
- Email change/deactivation/deletion and 2FA setup require password reauthentication.
- Recovery codes are random, keyed-hashed, and consumed under a lock.

Do not weaken error uniformity or expose “email exists” validation on anonymous recovery endpoints. Registration conflicts necessarily indicate that submitted identity is unavailable; add bot/abuse controls appropriate to the deployment.

## Sessions and tokens

Session cookies are HttpOnly, SameSite=Lax, and Secure in production. Django rotates the session key on login. The device model stores a keyed hash and encrypted server-side session reference; raw secrets are excluded from admin/logs.

JWT access tokens are short-lived. Refresh tokens rotate, are recorded in the outstanding table, and old values are blacklisted. Logout blacklists the supplied refresh token. Password reset/change, email change, bans, deactivation, and deletion blacklist outstanding refresh tokens as appropriate. Account-aware JWT authentication denies current bans/state even before access expiry.

For maximum token-theft resistance, reduce access lifetime and use sender-constrained tokens at an API gateway. Never store bearer tokens in browser local storage when an HttpOnly session architecture is available.

## Authorization and IDOR prevention

The backend is authoritative. Never trust role, permission, user, tenant, or ownership values supplied by a client. Add only allowlisted writable serializer fields. Filter a queryset to the current owner/tenant before object lookup; then apply object permission checks. UUIDs reduce guessability but are not authorization.

API keys are denied unless a view explicitly declares required scopes. Adding a view without a scope therefore fails closed for API-key callers. RBAC endpoints additionally require `roles.manage`; explicit user deny wins over every custom grant, including superuser.

Review every new route for:

- anonymous/session/JWT/API-key credential suitability;
- global permission and object ownership;
- writable foreign keys and mass assignment;
- allowed filters/ordering and data inference;
- side effects, idempotency, audit, and race control.

## CSRF, CORS, XSS, and redirects

Session-authenticated unsafe requests require CSRF. Do not decorate APIs with `csrf_exempt`. JavaScript reads the non-HttpOnly CSRF token cookie and submits `X-CSRFToken`; the authenticated session cookie remains HttpOnly.

CORS is allowlist-only and credentials are enabled for configured frontends. Never set wildcard origins with credentials. `CSRF_TRUSTED_ORIGINS` is a separate explicit list.

Django templates autoescape. Do not mark user content safe. The CSP middleware emits the configured strategy; adapt it to actual frontend assets, prefer nonces/hashes, and verify admin/docs after tightening. Validate redirects against an explicit host/scheme allowlist; no built-in auth flow accepts a client redirect URL.

## HTTPS and reverse proxies

Terminate TLS with modern settings. Production enables secure cookies, HTTPS redirect, one-year HSTS with subdomains/preload, nosniff, strict-origin referrer policy, frame denial, CSP, and a restrictive permissions policy.

Only enable `TRUST_PROXY_HEADERS` when:

1. the application port is unreachable except from controlled proxies;
2. the proxy overwrites, rather than appends blindly to, forwarded headers;
3. `TRUSTED_PROXY_IPS` contains only those direct proxy addresses;
4. health checks and local calls still use expected scheme/host values.

The IP helper ignores forwarded client IPs unless the direct peer is allowlisted. Django’s forwarded-protocol trust still depends on network isolation; an allowlisted compromised proxy is trusted.

## Database and Redis

Use TLS where services cross untrusted networks, private network policies, separate credentials, backups, point-in-time recovery, and least privileges. The application database role should not own the database. For stronger audit immutability, deny UPDATE/DELETE on the audit table and grant a separate retention role.

Redis is security-sensitive state, not an optional production optimization. Require authentication/TLS/network isolation as provided by the platform, disable public exposure, configure eviction intentionally, and alert on unavailability. Security controls fail visibly rather than silently disappearing.

## Email

Configure SPF, DKIM, and DMARC for the sending domain. Verification/reset/delete links contain single-use bearer secrets; use HTTPS, short expiry, and prevent referrer leakage on frontend landing pages. Do not embed sensitive personal data in email. Treat provider webhooks as untrusted signed inputs if added.

## File uploads

Every upload context must instantiate `SecureFileValidator` with the smallest extension/MIME allowlist and size limit. Client filename and declared MIME are untrusted. Store media on a separate origin/object store without script execution, with randomized names and private ACLs/signed URLs where appropriate.

Image decoding can be resource-intensive despite dimension checks; use process/container limits. Integrate malware scanning before marking untrusted documents downloadable, enforce quotas, and never let user input select arbitrary storage paths. Avoid serving SVG/HTML unless sanitized and isolated.

## Webhooks and SSRF

Outgoing endpoints require allowed HTTP schemes (HTTPS in production), no embedded credentials, and global resolved IPs. Redirects are disabled, requests time out, response bodies are truncated, and deliveries are HMAC-signed. DNS can change between validation and connection; enforce egress firewall/proxy policy that blocks private, metadata, loopback, and link-local ranges. Revalidate on every attempt, as the service does.

Consumers should verify signature with constant-time comparison, timestamp tolerance, and event-ID replay protection.

## Celery

Broker access permits task submission. Isolate Redis, accept JSON only, keep task arguments non-secret, validate identifiers/state again in tasks, set time/memory limits at worker/platform level, and run workers as non-root. Do not use pickle. Run one Beat instance. A task retry must not duplicate a state transition or bypass authorization.

## Logging, audit, and Sentry

Request logs include request ID, user ID, method, path without query string, status, duration, and validated IP. The sanitizer redacts password, authorization/cookie/token/secret/API-key/TOTP/recovery/session/encrypted fields. Do not add request bodies or full headers to logs.

Sentry is opt-in and uses `send_default_pii=False`. Review custom context before attaching it. Send audit/security streams to monitored storage and alert on lockouts, role/permission changes, bans, 2FA changes, key creation/revocation, and unusual session activity.

## Deployment checklist

- `DEBUG=false`; production settings module selected
- unique strong secrets from a secret manager
- explicit `ALLOWED_HOSTS`, CORS, CSRF, and trusted proxy values
- PostgreSQL/Redis private and protected; backups restored in a drill
- HTTPS, HSTS, cookies, CSP, static/media origins verified
- real email delivery and security templates tested
- migrations reviewed and applied once; bootstrap run
- `python manage.py check --deploy` clean or exceptions documented
- workers/Beat and readiness probes healthy
- object permissions/API-key scopes reviewed for every route
- dependency/container vulnerability scans and full tests green
- audit retention, privacy deletion, incident contacts, and monitoring approved

## Incident response

Preserve logs/audit evidence, contain affected credentials/sessions/keys, assess data scope, rotate only with dependency impact understood, patch and test, notify according to applicable policy/law, and document follow-up. Use account/session/API-key revocation services so security events and audit records are retained.
