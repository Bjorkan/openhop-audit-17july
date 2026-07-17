# BUG-007 — implementation plan

[← Finding](../../findings/BUG-007-advert-rate-limit-update-reports-immediate-success-after-save-failure.md) · [← Audit index](../../README.md)

> This is a planning document, not a ready-to-apply patch. Revalidate line numbers and surrounding code against the branch being changed.
> Reverification status: **confirmed against the supplied snapshot**.

| Field | Value |
|---|---|
| Finding | **Advert-rate-limit update reports immediate success after save or live-update failure** |
| Classification | **Confirmed defect** |
| Severity | **Medium** |
| Confidence | **Confirmed** |
| Area | Configuration persistence / UI contract |
| Components | OpenHop Repeater |
| Audit date | 2026-07-17 |

## Objective

Fix the confirmed defect: Persistence failure must be an API failure. A successful save with failed live reload must clearly require restart.

## Current behavior to preserve in the reproduction

The response exposes `persisted: false` and `live_update: false` inside a `success: true` result, while hard-coding `restart_required: false` and an immediate-success message.

## Required outcome

Use the same result handling as the duty-cycle and radio endpoints, including rollback or a restart-required response.

## Repositories and files to inspect or change

| Repository | Path | Purpose |
|---|---|---|
| OpenHop Repeater | `repeater/web/api_endpoints.py` | Evidence lines 2093–2142 |
| OpenHop Repeater | `repeater/config_manager.py` | Evidence lines 359–417 |

The listed paths are the minimum evidence/change surface identified by the audit. Before editing, search the repositories for the affected symbols, field names and response keys to find indirect consumers, tests and generated artifacts.

## Implementation work packages

1. Stop constructing success responses before `ConfigManager.update_and_save()` has produced a definitive persistence and live-apply result.
2. Use a shared API adapter for configuration commits that maps save failure, live-apply failure and restart-required outcomes consistently.
3. Do not leave the in-memory limiter on values that were not persisted. Either roll back runtime state or persist first and request restart.
4. Return the effective runtime values in the success payload so the UI can confirm what is active.

## Decisions and assumptions to double-check

- [ ] Confirm whether live-apply failure after durable save should roll back or require restart.
- [ ] Check endpoint HTTP status conventions.
- [ ] Verify no background reload can later contradict the response.

## Test plan

### Existing test modules likely to extend

- OpenHop Repeater: `tests/test_config_manager.py`
- OpenHop Repeater: `tests/test_handler_helpers_acl_advert.py`
- OpenHop Repeater: `tests/test_api_endpoints_core_coverage.py` and the domain-specific endpoint test module

### Required test cases

- [ ] Add a focused regression test that reproduces the current defect before the implementation and fails for the documented reason.
- [ ] Add a success-path test proving the effective runtime state, persisted state and API/UI-visible state agree after the change where those layers are involved.
- [ ] Add contract tests with representative serialized responses/requests and a frontend test for the displayed state.
- [ ] Add deterministic ordering/race tests using barriers or fake executors; do not rely on timing sleeps.
- [ ] Add failure-path tests for validation, persistence and live-apply failures where those stages are involved.
- [ ] Run both complete project suites and the audit reproduction checks after the focused tests pass.

### Manual or integration verification

- [ ] Repeat the exact scenario from the finding and record the before/after effective runtime values.
- [ ] Restart the service and verify persisted behavior remains correct where persistence is expected.
- [ ] Exercise a negative/failure path and confirm no partial in-memory or durable state remains.
- [ ] Verify logs and metrics describe the real outcome without reporting success prematurely.

## Compatibility, rollout and rollback

- No special deployment note beyond the repository’s normal staged rollout and rollback process.

- Keep the previous behavior behind a temporary compatibility alias/adapter only when an external contract requires it.
- Make rollback possible without hand-editing corrupted state. Configuration/data migrations need an explicit reverse or safe fallback path.
- Update documentation, OpenAPI/UI text and examples in the same change when user-visible semantics or field names change.

## Definition of done

- [ ] The behavior described in `BUG-007-advert-rate-limit-update-reports-immediate-success-after-save-failure.md` can no longer be reproduced.
- [ ] Runtime behavior, persisted configuration/queue state and API/UI telemetry agree for the affected operation.
- [ ] Failure paths return an explicit failure or restart-required result and do not silently commit partial state.
- [ ] A regression test fails on the supplied snapshot and passes with the implementation.

## Suggested implementation order

1. Add or isolate the failing regression test.
2. Introduce the smallest shared model/helper or transaction boundary required by this finding.
3. Migrate the affected runtime path and its direct consumers.
4. Add failure, restart and compatibility tests.
5. Run focused tests, both full project suites, static checks and the audit reproduction checks.
6. Rebuild generated frontend/API artifacts where applicable and verify no stale contract remains.
