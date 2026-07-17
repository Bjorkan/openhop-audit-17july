# BUG-003 — implementation plan

[← Finding](../../findings/BUG-003-live-duty-cycle-limit-changes-do-not-update-the-enforced-limit.md) · [← Audit index](../../README.md)

> This is a planning document, not a ready-to-apply patch. Revalidate line numbers and surrounding code against the branch being changed.
> Reverification status: **confirmed against the supplied snapshot**.

| Field | Value |
|---|---|
| Finding | **Live duty-cycle limit changes do not update the enforced limit** |
| Classification | **Confirmed defect** |
| Severity | **High** |
| Confidence | **Confirmed** |
| Area | Duty-cycle enforcement |
| Components | OpenHop Repeater |
| Audit date | 2026-07-17 |

## Objective

Fix the confirmed defect: The enforced limit shown in configuration and the runtime limit used by `can_transmit()` must change atomically.

## Current behavior to preserve in the reproduction

`AirtimeManager.__init__` caches `max_airtime_per_minute`. `update_duty_cycle_config` changes the shared config and requests a live update, but `ConfigManager.live_update_daemon` has no duty-cycle reload path. Enforcement therefore uses the old numeric limit until restart.

## Required outcome

Add `AirtimeManager.reload_config()` or read a validated immutable snapshot on each decision; invoke it during duty-cycle live updates and report `restart_required` when it cannot be applied.

## Repositories and files to inspect or change

| Repository | Path | Purpose |
|---|---|---|
| OpenHop Repeater | `repeater/airtime.py` | Evidence lines 10–28 |
| OpenHop Repeater | `repeater/web/api_endpoints.py` | Evidence lines 1925–1978 |
| OpenHop Repeater | `repeater/config_manager.py` | Evidence lines 286–353 |

The listed paths are the minimum evidence/change surface identified by the audit. Before editing, search the repositories for the affected symbols, field names and response keys to find indirect consumers, tests and generated artifacts.

## Implementation work packages

1. Add a validated runtime snapshot for duty-cycle settings or a dedicated `AirtimeManager.reload_config()` method. Avoid reading partially mutated shared dictionaries during a transmission decision.
2. Extend the live-update path in `ConfigManager` so the duty-cycle section updates the runtime manager after persistence succeeds.
3. Return a structured apply result. If no live manager exists or reload fails, persist only when the product contract allows restart-required changes and report `restart_required: true`; otherwise roll back.
4. Ensure the API response reports the value actually enforced, not only the value stored in YAML.

## Decisions and assumptions to double-check

- [ ] Confirm save-before-apply versus apply-before-save policy and rollback behavior.
- [ ] Check concurrent TX decisions cannot observe a half-updated limit.
- [ ] Verify disabled enforcement and extreme limit values.

## Test plan

### Existing test modules likely to extend

- OpenHop Repeater: `tests/test_airtime.py`
- OpenHop Repeater: `tests/test_config_manager.py`
- OpenHop Repeater: `tests/test_api_endpoints_core_coverage.py` and the domain-specific endpoint test module

### Required test cases

- [ ] Add a focused regression test that reproduces the current defect before the implementation and fails for the documented reason.
- [ ] Add a success-path test proving the effective runtime state, persisted state and API/UI-visible state agree after the change where those layers are involved.
- [ ] Use a fake clock and boundary cases immediately before, at and after the configured window/limit.
- [ ] Add deterministic ordering/race tests using barriers or fake executors; do not rely on timing sleeps.
- [ ] Add failure-path tests for validation, persistence and live-apply failures where those stages are involved.
- [ ] Run both complete project suites and the audit reproduction checks after the focused tests pass.

### Manual or integration verification

- [ ] Repeat the exact scenario from the finding and record the before/after effective runtime values.
- [ ] Restart the service and verify persisted behavior remains correct where persistence is expected.
- [ ] Exercise a negative/failure path and confirm no partial in-memory or durable state remains.
- [ ] Verify logs and metrics describe the real outcome without reporting success prematurely.

## Compatibility, rollout and rollback

- Exercise the change with representative hardware or a wrapper-level hardware simulator before production rollout.

- Keep the previous behavior behind a temporary compatibility alias/adapter only when an external contract requires it.
- Make rollback possible without hand-editing corrupted state. Configuration/data migrations need an explicit reverse or safe fallback path.
- Update documentation, OpenAPI/UI text and examples in the same change when user-visible semantics or field names change.

## Definition of done

- [ ] The behavior described in `BUG-003-live-duty-cycle-limit-changes-do-not-update-the-enforced-limit.md` can no longer be reproduced.
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
