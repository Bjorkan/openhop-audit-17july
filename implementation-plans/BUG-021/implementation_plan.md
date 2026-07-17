# BUG-021 — implementation plan

[← Finding](../../findings/BUG-021-a-version-result-from-the-old-update-channel-can-be-shown-as-the-result-for-a-new-channel.md) · [← Audit index](../../README.md)

> This is a planning document, not a ready-to-apply patch. Revalidate line numbers and surrounding code against the branch being changed.
> Reverification status: **confirmed against the supplied snapshot**.

| Field | Value |
|---|---|
| Finding | **A version result from the old update channel can be shown as the result for a new channel** |
| Classification | **Confirmed defect** |
| Severity | **Medium** |
| Confidence | **Confirmed** |
| Area | Self-update channel state |
| Components | OpenHop Repeater Web API |
| Audit date | 2026-07-17 |

## Objective

Fix the confirmed defect: A result must be tagged with the channel and generation that produced it. Stale results should be discarded.

## Current behavior to preserve in the reproduction

`set_channel()` invalidates cached values, but an already-running `_do_check()` later calls `_finish_check(latest)` and repopulates them. The status snapshot combines the new `channel` with a `latest_version` fetched from the old channel.

## Required outcome

Pass `(operation_id, channel)` into the worker and validate both at completion, or block channel changes while checking.

## Repositories and files to inspect or change

| Repository | Path | Purpose |
|---|---|---|
| OpenHop Repeater | `repeater/web/update_endpoints.py` | Evidence lines 351–410 |

The listed paths are the minimum evidence/change surface identified by the audit. Before editing, search the repositories for the affected symbols, field names and response keys to find indirect consumers, tests and generated artifacts.

## Implementation work packages

1. Capture the selected channel and operation ID when starting a version check.
2. At completion, update available-version state only when both still match. Otherwise discard the stale result.
3. Choose whether channel changes are blocked during active work or allowed with cancellation/invalidation; encode that choice in the state machine.
4. Clear channel-specific cached version/error data when switching channels.

## Decisions and assumptions to double-check

- [ ] Check cached version data is keyed by channel.
- [ ] Define behavior when changing channel during install.
- [ ] Verify errors are also channel-scoped.

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

- [ ] The behavior described in `BUG-021-a-version-result-from-the-old-update-channel-can-be-shown-as-the-result-for-a-new-channel.md` can no longer be reproduced.
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
