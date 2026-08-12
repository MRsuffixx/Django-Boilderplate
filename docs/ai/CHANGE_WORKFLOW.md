# AI Change Workflow

Use this sequence for every non-trivial change:

```text
UNDERSTAND -> INSPECT -> PLAN -> IMPLEMENT -> TEST -> REVIEW -> DOCUMENT
```

## 1. Understand

Restate the requested outcome and constraints. Read root and applicable nested `AGENTS.md`, relevant AI rules, developer docs, and ADRs. Decide whether the request is a reusable foundation change or product-domain work.

Exit condition: you can explain where the change belongs and which invariants it must preserve.

## 2. Inspect

Search before editing. Trace current models, services, selectors/querysets, views, settings, permissions, tasks, migrations, tests, and docs. Find a comparable existing flow. Check the worktree and preserve unrelated user changes.

Exit condition: you know what already exists, all consumers likely affected, and whether any request assumption is incorrect.

## 3. Plan

Choose the smallest coherent design that extends existing abstractions. Identify security/permission/ownership implications, transactions/concurrency, database portability, optional infrastructure, migrations, tests, and documentation. Surface any meaningful scope/authority decision before taking it.

Exit condition: each planned edit has an owning layer and validation method.

## 4. Implement

Edit in small, reviewable batches. Keep transport thin, mutations in services, reads in constrained querysets/selectors, and side effects behind existing boundaries. Add tests and migrations with the code. Do not perform opportunistic rewrites.

Exit condition: the requested behavior is complete, not scaffolded or represented by placeholders.

## 5. Test

Run targeted tests while iterating. Then run the default Django/pytest/Ruff checks from `TESTING_RULES.md`. Validate fresh migrations/schema/optional-disabled behavior when relevant. Do not test Docker unless explicitly requested.

Exit condition: proportionate automated checks pass, and untested external behavior is clearly identified.

## 6. Review

Inspect the diff and surrounding code as if reviewing another engineer's change. Look for permission bypass, IDOR, secret leakage, race conditions, optional dependency leaks, SQLite/PostgreSQL incompatibility, N+1 queries, duplicate abstractions, dead code, TODOs, inaccurate names, migration quality, and unrelated modifications.

Exit condition: every confirmed issue is fixed or explicitly reported as outside the authorized scope.

## 7. Document

Update public developer docs for behavior/configuration changes. Update `AGENTS.md`, a relevant ADR, `PROJECT_CONTEXT.md`, or `PROJECT_STATE.md` only when the architecture/rule/current state they describe actually changed. Update `CHANGELOG.md` for meaningful version history, not for routine AI narration.

Exit condition: a new human or AI agent will not be misled by stale documentation.

## Handoff format

Lead with the outcome. Summarize changed architecture/behavior, key files, validation evidence, and manual/external checks remaining. Do not claim completion beyond the evidence.
