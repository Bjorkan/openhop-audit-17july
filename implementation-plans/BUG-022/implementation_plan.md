# BUG-022 — implementation plan

[← Finding](../../findings/BUG-022-update-channel-persistence-failure-is-hidden-behind-a-success-response.md) · [← Audit index](../../README.md)

> This is a planning document, not a ready-to-apply patch. Revalidate line numbers and surrounding code against the branch being changed.

| Field | Value |
|---|---|
| Finding | **Update-channel persistence failure is hidden behind a success response** |
| Classification | **Confirmed defect** |
| Severity | **Medium** |
| Confidence | **Confirmed** |
| Area | Self-update persistence / UI contract |
| Components | OpenHop Repeater Web API |
| Audit date | 2026-07-17 |

## Objective

Fix the confirmed defect: The endpoint should report success only after durable persistence, or explicitly return a volatile runtime-only result.

## Current behavior to preserve in the reproduction

On read-only storage, permission failure or disk error, the running process uses the new channel until restart, while the persisted file remains unchanged. The UI receives success and has no way to know the selection will revert.

## Required outcome

Make `_save_channel()` return a boolean or raise; persist atomically before changing shared runtime state; return an HTTP error on failure.

## Repositories and files to inspect or change

| Repository | Path | Purpose |
|---|---|---|
| OpenHop Repeater | `repeater/web/update_endpoints.py` | Evidence lines 351–410 |

The listed paths are the minimum evidence/change surface identified by the audit. Before editing, search the repositories for the affected symbols, field names and response keys to find indirect consumers, tests and generated artifacts.

## Implementation work packages

1. Make channel persistence return a definitive result or raise an error; do not log-and-continue into a success response.
2. Persist atomically before publishing the new channel to running state. On failure retain the old channel everywhere.
3. Return an error status/envelope that the frontend can display and retry.
4. Verify behavior for read-only filesystem, disk-full simulation, invalid path and interrupted write.

## Decisions and assumptions to double-check

- [ ] Preserve old state until fsync/replace succeeds.
- [ ] Check file permissions/ownership.
- [ ] Ensure UI does not optimistically switch channel before success.

## Test plan

### Existing test modules likely to extend

- OpenHop Repeater: `tests/test_config_manager.py`
- OpenHop Repeater: `tests/test_api_endpoints_core_coverage.py` and the domain-specific endpoint test module
- OpenHop Repeater: `tests/test_update_endpoints_unit.py`

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

- Do not test updater installation against the production service first; use an isolated installation and simulate stale worker completions.

- Keep the previous behavior behind a temporary compatibility alias/adapter only when an external contract requires it.
- Make rollback possible without hand-editing corrupted state. Configuration/data migrations need an explicit reverse or safe fallback path.
- Update documentation, OpenAPI/UI text and examples in the same change when user-visible semantics or field names change.

## Definition of done

- [ ] The behavior described in `BUG-022-update-channel-persistence-failure-is-hidden-behind-a-success-response.md` can no longer be reproduced.
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
