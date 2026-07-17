# BUG-020 — implementation plan

[← Finding](../../findings/BUG-020-an-update-install-can-overlap-a-version-check-and-be-reported-idle-while-still-running.md) · [← Audit index](../../README.md)

> This is a planning document, not a ready-to-apply patch. Revalidate line numbers and surrounding code against the branch being changed.

| Field | Value |
|---|---|
| Finding | **An update install can overlap a version check and be reported idle while still running** |
| Classification | **Confirmed defect** |
| Severity | **High** |
| Confidence | **Confirmed** |
| Area | Self-update state machine |
| Components | OpenHop Repeater Web API |
| Audit date | 2026-07-17 |

## Objective

Fix the confirmed defect: Only one updater operation may own the state. Completion from an obsolete worker must not mutate the current job.

## Current behavior to preserve in the reproduction

`start_install()` accepts every state except `installing`. `_finish_check()` unconditionally writes `state="idle"`. The API therefore permits check→install overlap; completion order determines the visible state and can enable a second install while the first one is active.

## Required outcome

Use an explicit transition table plus monotonically increasing operation IDs. `finish_check(id, ...)` and `finish_install(id, ...)` should no-op unless the ID and operation type still match.

## Repositories and files to inspect or change

| Repository | Path | Purpose |
|---|---|---|
| OpenHop Repeater | `repeater/web/update_endpoints.py` | Evidence lines 393–447 |

The listed paths are the minimum evidence/change surface identified by the audit. Before editing, search the repositories for the affected symbols, field names and response keys to find indirect consumers, tests and generated artifacts.

## Implementation work packages

1. Replace the shared mutable update-status string with an operation record containing an increasing ID, operation type, channel, state and timestamps.
2. Enforce an explicit transition table so check and install cannot overlap unless deliberately supported.
3. Require worker completion to present the same operation ID/type before mutating shared state; stale completions must be ignored and logged.
4. Expose operation identity and current state consistently through the API and UI polling path.

## Decisions and assumptions to double-check

- [ ] Define whether install automatically cancels/checks or must reject while busy.
- [ ] Check process restart during an operation.
- [ ] Ensure locks are not held during network/subprocess work.

## Test plan

### Existing test modules likely to extend

- OpenHop Repeater: `tests/test_api_endpoints_core_coverage.py` and the domain-specific endpoint test module
- OpenHop Repeater: `tests/test_update_endpoints_unit.py`

### Required test cases

- [ ] Add a focused regression test that reproduces the current defect before the implementation and fails for the documented reason.
- [ ] Add a success-path test proving the effective runtime state, persisted state and API/UI-visible state agree after the change where those layers are involved.
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

- [ ] The behavior described in `BUG-020-an-update-install-can-overlap-a-version-check-and-be-reported-idle-while-still-running.md` can no longer be reproduced.
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
