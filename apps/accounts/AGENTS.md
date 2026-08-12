# Accounts module instructions

Read `/AGENTS.md` first. These rules apply to `apps/accounts/`.

- This app owns durable identity data: `User`, `UserProfile`, `UserPreferences`, `UserSecuritySettings`, `UserBan`, and `AccountStatus`.
- Keep the main `User` model lean. Put optional presentation/preferences/security state in the existing one-to-one models unless the field is required for identity or authentication gating.
- Create users through `UserManager` or `AccountService`; email normalization and case-insensitive email/username constraints must remain intact.
- Account access must use `User.can_authenticate_now()`, not `is_active` alone.
- `BanService` owns ban/revoke transitions. Credential lifecycle, registration, deactivation, and deletion remain in `apps.authentication.services.AccountService`.
- State/ban changes must revoke applicable sessions/JWTs and create audit/security records through existing services.
- Never expose status, staff, superuser, role, or ownership fields as generically writable API fields.
- Avoid adding domain-specific profile fields. A product domain should own its own extension model/app.
- Test case-insensitive identity, account-state gates, active/future/expired bans, and concurrency-sensitive transitions.
