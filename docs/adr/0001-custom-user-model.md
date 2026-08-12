# Custom user model from project inception

## Status

Accepted

## Context

The foundation needs email/username login, UUID identity, account states, verification timestamps, security metadata, and future extension without a disruptive mid-project user migration. Django's built-in `User` model cannot be safely swapped after dependent migrations and data exist.

## Decision

Use `apps.accounts.models.User` from the first migration and set `AUTH_USER_MODEL = "accounts.User"`. The model derives from `AbstractBaseUser` and `PermissionsMixin`, uses email as `USERNAME_FIELD`, retains username as a unique login identifier, and uses `UserManager` for normalization/creation.

Keep the user focused on identity and authentication gating. Store profile, preference, and additional account-security state in `UserProfile`, `UserPreferences`, and `UserSecuritySettings`. Use `AccountStatus` and active bans in addition to `is_active` through `User.can_authenticate_now()`.

## Consequences

- Every user foreign key must reference `settings.AUTH_USER_MODEL` or the resolved model.
- Case-insensitive email/username integrity is enforced through normalization and database constraints.
- Changing the user model or app label later is a major data/migration project, not a rename.
- Product-specific user attributes should generally use domain-owned extension models rather than bloating `User`.
- Authentication backends/services must respect the full account gate, not only Django's `is_active` flag.
