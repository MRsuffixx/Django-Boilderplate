# Authorization module instructions

Read `/AGENTS.md` first. This app is the single permission/RBAC authority.

- Permissions are stable dotted codenames. Roles are permission collections, never application control-flow identities.
- Preserve resolution order: account gate -> explicit `DENY` -> explicit `ALLOW` -> superuser -> active role permissions -> deny.
- `DENY` must continue to override both role grants and custom-system superuser grants.
- Register definitions with `register_permissions()` and synchronize through the additive `bootstrap` command. Startup registration must not write to the database.
- Do not silently delete unknown permissions or system roles. Deprecation/removal requires an explicit reviewed process.
- Global permissions do not replace owner/tenant queryset restrictions.
- Keep time-bounded `UserRole` assignments and per-user overrides transactionally consistent and auditable.
- Never accept a role, permission, effect, `granted_by`, or target user from a client without explicit `roles.manage` authorization and serializer allowlisting.
- Tests must cover inactive accounts, explicit deny, explicit allow, superuser behavior, expired/future assignments, default deny, and object-level restrictions.
