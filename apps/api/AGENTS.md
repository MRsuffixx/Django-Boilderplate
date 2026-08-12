# API module instructions

Read `/AGENTS.md` and `docs/API.md` first. This app is an HTTP adapter, not a business-logic home.

- Keep routes under `/api/v1/` and preserve stable response/error envelopes.
- Views authenticate/authorize, validate with serializers, call services/selectors, and serialize results. Do not coordinate multi-model transitions in views.
- Serializers define transport fields and validation; never expose mass-assignable ownership, privilege, account-status, secret, or audit actor fields.
- Every collection/detail queryset must constrain visibility before object retrieval. Avoid IDOR-prone unrestricted `.get(pk=...)` calls.
- Administrative endpoints declare `HasPermission` plus `required_permission`; API-key-compatible endpoints declare exact scopes through `HasAPIKeyScope`.
- API keys are fail-closed: a view without a scope declaration is not API-key accessible.
- Explicitly allowlist filter, search, and ordering fields. Use bounded `StandardPagination`.
- Use existing throttle classes/scopes and `APIException` stable codes. Do not hand-build a competing envelope.
- Update/validate drf-spectacular schema and add negative authorization, ownership, throttle, and error-format tests for new endpoints.
