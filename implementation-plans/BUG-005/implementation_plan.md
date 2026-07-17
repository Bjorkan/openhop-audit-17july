# BUG-005 — implementation plan

[← Finding](../../findings/BUG-005-sx1262-live-radio-update-omits-transmit-power.md) · [← Audit index](../../README.md)

> This is a planning document, not a ready-to-apply patch. Revalidate line numbers and surrounding code against the branch being changed.
> Reverification status: **confirmed against the supplied snapshot**.

| Field | Value |
|---|---|
| Finding | **SX1262 live radio updates omit transmit power** |
| Classification | **Confirmed defect** |
| Severity | **Medium** |
| Confidence | **Confirmed** |
| Area | Radio configuration |
| Components | OpenHop Core + OpenHop Repeater |
| Audit date | 2026-07-17 |

## Objective

Fix the confirmed defect: Changing TX power must either call the hardware setter and verify success or be reported as requiring restart.

## Current behavior to preserve in the reproduction

The SX1262 wrapper has a separate `set_tx_power()` method and its `configure_radio()` signature does not include power. `ConfigManager` takes the configure branch and skips the fallback branch where power is handled.

## Required outcome

Use a capability-oriented radio adapter: apply modulation, then apply power when changed, and only mark live update successful if both operations succeed.

## Repositories and files to inspect or change

| Repository | Path | Purpose |
|---|---|---|
| OpenHop Repeater | `repeater/config_manager.py` | Evidence lines 76–149 |
| OpenHop Core | `src/openhop_core/hardware/sx1262_wrapper.py` | Evidence lines 1589–1598 |

The listed paths are the minimum evidence/change surface identified by the audit. Before editing, search the repositories for the affected symbols, field names and response keys to find indirect consumers, tests and generated artifacts.

## Implementation work packages

1. Extend the radio capability contract so transmit power is an explicit requested field with a success/failure result rather than an incidental wrapper attribute.
2. For SX1262, call the supported power setter when the requested power differs. Treat unsupported or failed application as a partial failure, not successful live application.
3. Keep the old power value in runtime state if application fails and ensure persistence/response semantics match the chosen rollback or restart-required policy.
4. Audit other hardware wrappers for the same omission before making the common adapter mandatory.

## Decisions and assumptions to double-check

- [ ] Confirm permitted power range per radio/region rather than relying only on UI range.
- [ ] Check wrapper return-value conventions and exceptions.
- [ ] Verify read-back is possible or document that success is command acceptance only.

## Test plan

### Existing test modules likely to extend

- OpenHop Repeater: `tests/test_config_manager.py`
- OpenHop Repeater: `tests/test_config_radio.py`, `tests/test_radio_config.py`
- OpenHop Core: `tests/test_sx1262_wrapper.py`, `tests/test_radio_capabilities.py`

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

- Exercise the change with representative hardware or a wrapper-level hardware simulator before production rollout.

- Keep the previous behavior behind a temporary compatibility alias/adapter only when an external contract requires it.
- Make rollback possible without hand-editing corrupted state. Configuration/data migrations need an explicit reverse or safe fallback path.
- Update documentation, OpenAPI/UI text and examples in the same change when user-visible semantics or field names change.

## Definition of done

- [ ] The behavior described in `BUG-005-sx1262-live-radio-update-omits-transmit-power.md` can no longer be reproduced.
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
