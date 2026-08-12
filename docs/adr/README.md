# Architecture Decision Records

ADRs explain why durable architectural choices in this repository exist. Read relevant records before reversing or bypassing a decision.

## Process

- Number new records sequentially as `NNNN-short-title.md`.
- Use the sections `Title`, `Status`, `Context`, `Decision`, and `Consequences`.
- Status is normally `Proposed`, `Accepted`, `Superseded by ADR NNNN`, or `Deprecated`.
- Do not rewrite an accepted decision to hide history. Add a superseding ADR when the decision materially changes.
- Create an ADR only for a choice with lasting architectural consequences, not routine implementation details.
- Update `/AGENTS.md`, `docs/ai/PROJECT_CONTEXT.md`, or `docs/ai/PROJECT_STATE.md` only when the decision changes their guidance/current-state claims.

## Current records

- [0001 — Custom user model from project inception](0001-custom-user-model.md)
- [0002 — UUID primary keys for application models](0002-uuid-primary-keys.md)
- [0003 — Explicit service layer for state changes](0003-service-layer.md)
- [0004 — Redis is optional infrastructure](0004-optional-redis.md)
- [0005 — SQLite and PostgreSQL are supported](0005-multiple-database-support.md)
- [0006 — Celery is optional infrastructure](0006-optional-celery.md)
