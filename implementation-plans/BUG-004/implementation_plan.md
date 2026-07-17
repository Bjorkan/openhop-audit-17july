# BUG-004 — implementation plan

[← Finding](../../findings/BUG-004-live-radio-changes-leave-airtime-estimation-on-the-old-modulation.md) · [← Audit index](../../README.md)

> This is a planning document, not a ready-to-apply patch. Revalidate line numbers and surrounding code against the branch being changed.

| Field | Value |
|---|---|
| Finding | **Live radio changes leave airtime estimation on the old modulation** |
| Classification | **Confirmed defect** |
| Severity | **High** |
| Confidence | **Confirmed** |
| Area | Radio configuration / duty-cycle enforcement |
| Components | OpenHop Core + OpenHop Repeater |
| Audit date | 2026-07-17 |

## Objective

Fix the confirmed defect: Hardware modulation and the parameters used to calculate airtime must be updated in the same successful operation.

## Current behavior to preserve in the reproduction

`AirtimeManager` copies radio values during construction. `ConfigManager` reconfigures the hardware and updates `repeater_handler.radio_config`, but it does not refresh the manager. The comment that the manager “has its own config reference that gets updated” is insufficient because calculations use cached scalar attributes.

## Required outcome

Reload airtime parameters only after hardware configuration succeeds; on failure keep both the old hardware and old accounting snapshot, or require restart.

## Repositories and files to inspect or change

| Repository | Path | Purpose |
|---|---|---|
| OpenHop Repeater | `repeater/airtime.py` | Evidence lines 10–28 |
| OpenHop Repeater | `repeater/config_manager.py` | Evidence lines 76–149 |
| OpenHop Repeater | `repeater/engine.py` | Evidence lines 1782–1815 |
| OpenHop Core | `src/openhop_core/hardware/sx1262_wrapper.py` | Verify the hardware apply contract used by Repeater |
| OpenHop Core | `src/openhop_core/protocol/packet_utils.py` | Verify canonical modulation/airtime semantics; locate the exact owning module if renamed |

The listed paths are the minimum evidence/change surface identified by the audit. Before editing, search the repositories for the affected symbols, field names and response keys to find indirect consumers, tests and generated artifacts.

## Implementation work packages

1. Represent radio parameters used for hardware and airtime estimation with the same validated immutable snapshot.
2. Apply the snapshot to hardware first and verify every requested field was accepted. Only then replace the airtime estimator snapshot and handler-visible radio configuration.
3. Define rollback semantics for wrappers that partially apply settings. If reliable rollback is unavailable, reject live application and require restart before mutating the persisted active configuration.
4. Confirm preamble length, bandwidth units, coding-rate representation and spreading-factor defaults are identical in Core, Repeater and the UI.

## Decisions and assumptions to double-check

- [ ] Verify hardware wrappers can report partial application reliably.
- [ ] Check airtime unit conversion against Core LoRa airtime implementation.
- [ ] Confirm changing frequency alone does not unnecessarily reset accounting history.

## Test plan

### Existing test modules likely to extend

- OpenHop Repeater: `tests/test_airtime.py`
- OpenHop Repeater: `tests/test_config_manager.py`
- OpenHop Repeater: `tests/test_config_radio.py`, `tests/test_radio_config.py`
- OpenHop Core: `tests/test_sx1262_wrapper.py`, `tests/test_radio_capabilities.py`
- OpenHop Repeater: `tests/test_engine.py`, `tests/test_flood_loop_dedup.py`

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

- [ ] The behavior described in `BUG-004-live-radio-changes-leave-airtime-estimation-on-the-old-modulation.md` can no longer be reproduced.
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
