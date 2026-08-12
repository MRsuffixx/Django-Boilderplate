# Security module instructions

Read `/AGENTS.md` and `docs/ai/SECURITY_RULES.md` first.

- `SecurityEvent` is user/security history, distinct from administrative `AuditLog`. Add new event types only for meaningful security lifecycle events.
- `LoginProtectionService` is the only login brute-force boundary. It hashes identifier/IP dimensions before storage.
- With Redis disabled, counters live in `LoginThrottleState`; with Redis enabled, the configured Django Redis cache is used. Preserve equivalent thresholds/backoff semantics.
- Never reveal stored dimension hashes or use them as authentication identifiers. Retention cleanup must stay bounded and configurable through task/command scheduling.
- An enabled Redis failure must not silently downgrade to local memory. Disabled mode must never attempt Redis.
- Persistent account lock updates and lock/unlock events must remain enumeration-safe.
- Security-event metadata must not contain passwords, submitted codes, raw identifiers when a hash suffices, tokens, secrets, or authorization headers.
- Security events are not a substitute for permission checks or audit records.
- Tests must cover both lock creation and reset/expiry behavior, including the database fallback used by minimal mode.
