# Authentication module instructions

Read `/AGENTS.md` and `docs/ai/SECURITY_RULES.md` first. Authentication changes require regression and bypass tests.

- Preserve the service boundaries in `services.py`: `TokenService`, `SessionService`, `TwoFactorService`, `AuthenticationService`, and `AccountService`.
- All authentication methods must re-check account eligibility, active bans, persistent lock state, and required 2FA. Do not create a shortcut backend or endpoint.
- One-time tokens remain random, keyed-hashed in storage, expiring, purpose-bound, superseding, and consumed under a row lock.
- JWT refresh tokens rotate and blacklist; security-sensitive credential changes revoke outstanding tokens and appropriate sessions.
- Tracked sessions store a hash plus encrypted server-side reference, never a raw reusable session secret in an API/admin/log.
- TOTP secrets remain encrypted; recovery codes remain keyed-hashed, shown once, and consumed once under a lock.
- Registration/reset/resend behavior must resist account enumeration. Do not vary public messages in a way that discloses account existence.
- Use transactions and `select_for_update()` for token consumption, recovery-code consumption, session revocation, and credential transitions.
- Send email/security/audit side effects through centralized services and preferably after commit.
- Never log passwords, submitted codes, tokens, session references, TOTP seeds, or recovery codes.
