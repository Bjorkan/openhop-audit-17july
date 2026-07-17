# BUG-001 — implementation plan

[← Finding](../../findings/BUG-001-duty-cycle-budget-usage-is-presented-as-actual-duty-cycle.md) · [← Audit index](../../README.md)

> This is a planning document, not a ready-to-apply patch. Revalidate line numbers and surrounding code against the branch being changed.
> Reverification status: **confirmed against the supplied snapshot**.

| Field | Value |
|---|---|
| Finding | **Duty-cycle budget usage is presented as actual duty cycle** |
| Classification | **Confirmed defect** |
| Severity | **Medium** |
| Confidence | **Confirmed** |
| Area | Telemetry and dashboard |
| Components | OpenHop Repeater + Web UI |
| Audit date | 2026-07-17 |

## Objective

Fix the confirmed defect: The data contract should expose both `actual_duty_percent = current_airtime_ms / 60000 * 100` and `budget_used_percent = current_airtime_ms / max_airtime_ms * 100`. UI labels and external telemetry should use the matching value.

## Current behavior to preserve in the reproduction

The backend divides rolling airtime by `max_airtime_per_minute`. The dashboard labels that result as “Duty Cycle” and compares it with `max_airtime_percent`, while Glass and storage publish the same ambiguous field. This also causes progress calculations to normalize an already-normalized value a second time.

## Required outcome

Introduce an explicit airtime snapshot with unambiguous names, preserve any legacy field temporarily with a deprecation note, and update the dashboard/Glass/storage consumers together.

## Repositories and files to inspect or change

| Repository | Path | Purpose |
|---|---|---|
| OpenHop Repeater | `repeater/airtime.py` | Evidence lines 104–116 |
| OpenHop Repeater | `repeater/engine.py` | Evidence lines 1577–1655 |
| OpenHop Repeater | `repeater/data_acquisition/glass_handler.py` | Evidence lines 304–325 |
| OpenHop Repeater | `repeater/data_acquisition/storage_collector.py` | Evidence lines 140–175 |
| OpenHop Repeater Web UI | `Frontend source corresponding to repeater/web/html/assets/ (not supplied)` | Locate before implementation; generated bundle must not be edited as source |

The listed paths are the minimum evidence/change surface identified by the audit. Before editing, search the repositories for the affected symbols, field names and response keys to find indirect consumers, tests and generated artifacts.

## Implementation work packages

1. Define one canonical airtime snapshot with explicit units and denominators: rolling window length, used airtime in milliseconds, configured limit in milliseconds, actual duty-cycle percentage, and percentage of budget consumed.
2. Change `AirtimeManager.get_stats()` to construct that snapshot. Keep `utilization_percent` only as a temporary compatibility alias for `budget_used_percent`, document the alias, and set a removal target.
3. Update the repeater engine stats payload, Glass payload, storage/MQTT records and every frontend consumer to use the explicit field matching its label. The dashboard value beside the configured limit must use `actual_duty_percent`; a progress bar may use `budget_used_percent`.
4. Search for all uses of `utilization_percent`, `current_airtime_ms`, `max_airtime_percent` and related labels to avoid leaving a mixed contract.

## Decisions and assumptions to double-check

- [ ] Confirm whether the configured percentage is legally/regulatorily a rolling 60-second limit or a different window.
- [ ] Check external consumers of Glass/MQTT fields before renaming.
- [ ] Verify zero/disabled limit behavior avoids division by zero.

## Test plan

### Existing test modules likely to extend

- OpenHop Repeater: `tests/test_airtime.py`
- OpenHop Repeater: `tests/test_mqtt_publish_integration.py`, `tests/test_storage_collector_ws_stats_throttle.py`
- OpenHop Repeater: `tests/test_engine.py`, `tests/test_flood_loop_dedup.py`

### Required test cases

- [ ] Add a focused regression test that reproduces the current defect before the implementation and fails for the documented reason.
- [ ] Add a success-path test proving the effective runtime state, persisted state and API/UI-visible state agree after the change where those layers are involved.
- [ ] Use a fake clock and boundary cases immediately before, at and after the configured window/limit.
- [ ] Add contract tests with representative serialized responses/requests and a frontend test for the displayed state.
- [ ] Add failure-path tests for validation, persistence and live-apply failures where those stages are involved.
- [ ] Run both complete project suites and the audit reproduction checks after the focused tests pass.

### Manual or integration verification

- [ ] Repeat the exact scenario from the finding and record the before/after effective runtime values.
- [ ] Restart the service and verify persisted behavior remains correct where persistence is expected.
- [ ] Exercise a negative/failure path and confirm no partial in-memory or durable state remains.
- [ ] Verify logs and metrics describe the real outcome without reporting success prematurely.

## Compatibility, rollout and rollback

- The supplied snapshot contains compiled frontend assets but no `.vue`, `.ts` or `.tsx` source. Apply UI work in the actual source repository, rebuild, then replace generated assets.
- Treat field renames/envelope changes as a compatibility migration. Keep aliases or version the API where external clients may depend on the old contract.

- Keep the previous behavior behind a temporary compatibility alias/adapter only when an external contract requires it.
- Make rollback possible without hand-editing corrupted state. Configuration/data migrations need an explicit reverse or safe fallback path.
- Update documentation, OpenAPI/UI text and examples in the same change when user-visible semantics or field names change.

## Definition of done

- [ ] The behavior described in `BUG-001-duty-cycle-budget-usage-is-presented-as-actual-duty-cycle.md` can no longer be reproduced.
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
