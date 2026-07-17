# BUG-011 — implementation plan

[← Finding](../../findings/BUG-011-gps-clock-corrections-can-reset-rolling-airtime-and-rate-limit-windows.md) · [← Audit index](../../README.md)

> This is a planning document, not a ready-to-apply patch. Revalidate line numbers and surrounding code against the branch being changed.
> Reverification status: **confirmed against the supplied snapshot**.

| Field | Value |
|---|---|
| Finding | **GPS wall-clock corrections can invalidate rolling airtime and rate-limit windows** |
| Classification | **Confirmed defect** |
| Severity | **High** |
| Confidence | **Confirmed** |
| Area | Timekeeping / safety limits |
| Components | OpenHop Repeater |
| Audit date | 2026-07-17 |

## Objective

Fix the confirmed defect: Elapsed-time logic must use a monotonic clock. Wall clock should be reserved for persisted/event timestamps displayed to users.

## Current behavior to preserve in the reproduction

A forward clock correction makes old TX records, advert dedupe entries, token-bucket timestamps and penalties appear expired immediately. A backward correction can hold them active much longer than intended. The airtime limiter can consequently allow a second full budget without 60 seconds of real elapsed time.

## Required outcome

Convert AirtimeManager, advert limiter and other in-process cooldowns to `time.monotonic()`; inject the clock for deterministic tests. Keep UTC timestamps separately where needed.

## Repositories and files to inspect or change

| Repository | Path | Purpose |
|---|---|---|
| OpenHop Repeater | `repeater/airtime.py` | Evidence lines 70–97 |
| OpenHop Repeater | `repeater/data_acquisition/gps_service.py` | Evidence lines 193–197 |
| OpenHop Repeater | `repeater/config.py` | Evidence lines 262–277 |
| OpenHop Repeater | `repeater/handler_helpers/advert.py` | Evidence lines 430–480 |

The listed paths are the minimum evidence/change surface identified by the audit. Before editing, search the repositories for the affected symbols, field names and response keys to find indirect consumers, tests and generated artifacts.

## Implementation work packages

1. Classify every use of time as either wall-clock timestamp or elapsed-time control. Rolling windows, token buckets, cooldowns, deduplication, penalties and hysteresis must use monotonic time.
2. Keep UTC/wall-clock values only for persisted human-readable event timestamps and externally meaningful dates.
3. Inject a clock abstraction into AirtimeManager and advert/rate-limit components so tests can advance time without sleeping.
4. Define restart semantics for persisted state that currently stores wall-clock values; migrate or discard incompatible transient timer state safely.

## Decisions and assumptions to double-check

- [ ] Do not persist raw monotonic timestamps across restart.
- [ ] Check GPS/NTP synchronization code for intentional wall-clock use.
- [ ] Review all rate limiters, not only the two reproduced paths.

## Test plan

### Existing test modules likely to extend

- OpenHop Repeater: `tests/test_airtime.py`
- OpenHop Repeater: `tests/test_handler_helpers_acl_advert.py`

### Required test cases

- [ ] Add a focused regression test that reproduces the current defect before the implementation and fails for the documented reason.
- [ ] Add a success-path test proving the effective runtime state, persisted state and API/UI-visible state agree after the change where those layers are involved.
- [ ] Use a fake clock and boundary cases immediately before, at and after the configured window/limit.
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

- [ ] The behavior described in `BUG-011-gps-clock-corrections-can-reset-rolling-airtime-and-rate-limit-windows.md` can no longer be reproduced.
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
