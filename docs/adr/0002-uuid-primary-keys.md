# UUID primary keys for application models

## Status

Accepted

## Context

The boilerplate is intended for APIs, integrations, distributed deployments, imports, and independently developed future domains. Sequential public identifiers are easy to enumerate and can complicate cross-system data creation. Django/third-party framework tables may still use their native keys.

## Decision

Use `common.models.UUIDModel` for application-owned entities. It provides a non-editable UUID4 primary key. Compose it with `TimeStampedModel` or other explicit base models only when their semantics are needed.

Do not force UUIDs onto Django or third-party tables whose migrations are externally owned.

## Consequences

- URLs and API serializers expose opaque UUID strings for application resources.
- UUID opacity is not authorization; querysets and permissions must still prevent IDOR.
- Foreign keys and tests should use model instances/UUIDs rather than assuming integers.
- UUID indexes are larger than integer indexes, so additional indexes must remain intentional.
- Future product-domain models should use `UUIDModel` by default unless a documented interoperability reason requires another identity strategy.
