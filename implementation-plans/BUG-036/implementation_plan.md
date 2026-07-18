# BUG-036 — implementation plan

[← Finding](../../findings/BUG-036-usb-live-radio-settings-never-reach-the-modem.md) · [← Audit index](../../README.md)

> This is a planning document, not a ready-to-apply patch. Revalidate line numbers and surrounding code against the branch being changed.
> Verification status: **three independent checks passed against the supplied snapshots**.

| Field | Value |
|---|---|
| Finding | **USB live radio setters report success without sending configuration to the modem** |
| Classification | **Confirmed defect** |
| Severity | **High** |
| Confidence | **Triple-verified** |
| Area | USB radio live configuration |
| Components | OpenHop Core + OpenHop Repeater |
| Audit date | 2026-07-17 |

## Objective

Eliminate the confirmed contract violation without changing adjacent behavior that is not required by this finding.

## Current behavior

The USB adapter’s live setters only modify Python attributes and return `True`. Repeater `ConfigManager` treats those return values as successful hardware application, so runtime/UI state can claim the radio changed while the modem retains its previous settings.

## Required outcome

A successful live update must issue the corresponding modem command and confirm acceptance, or explicitly report restart required/unsupported.

## Repositories and files to inspect or change

| Repository | Path | Purpose |
|---|---|---|
| OpenHop Core | `src/openhop_core/hardware/usb_radio.py` | Confirmed evidence and primary change surface |
| OpenHop Repeater | `repeater/config_manager.py` | Confirmed evidence and primary change surface |

Before editing, search both repositories for every affected symbol, configuration key, response field and test double. Generated assets and external firmware interfaces must be updated only when they are actual consumers of the corrected contract.

## Implementation work packages

1. Implement setters using the modem command protocol, preferably via one atomic `set_config` operation.
2. Expose radio capabilities so Repeater can distinguish live-supported, restart-required, and failed changes.
3. Do not update effective fields until the modem accepts the command.

## Decisions and assumptions to double-check

- [ ] Verify firmware command support and whether changing modulation while RX is active requires a mode transition.
- [ ] Ensure the same correction does not duplicate initial configuration on reconnect.

## Test plan

### Existing test modules likely to extend

- OpenHop Core: `tests/test_radio_capabilities.py`
- OpenHop Repeater: `tests/test_config_manager.py`
- OpenHop Repeater: `tests/test_config_radio.py`

### Required focused tests

- [ ] Preserve verification method 1: static setter trace — All ConfigManager-visible setters only assign attributes and return true.
- [ ] Preserve verification method 2: direct setter — Frequency changes locally with zero serial writes.
- [ ] Preserve verification method 3: configmanager integration — Repeater reports live-update success while zero modem writes occur.
- [ ] Add at least one negative test proving unrelated traffic/state is not changed by the correction.
- [ ] Add failure, timeout, cancellation or restart coverage where the affected path owns resources or persistence.
- [ ] Ensure the regression test fails for the documented reason on the supplied snapshot and passes after the implementation.

### Integration verification

- [ ] Exercise the real public entry point, not only the isolated helper.
- [ ] Verify effective runtime state, persisted state and user-visible status agree.
- [ ] Run the complete Core and Repeater suites plus all five triple-verification scripts.
- [ ] Re-test with the relevant real hardware/firmware where the finding concerns a physical adapter; the audit uses deterministic fakes for reproducibility.

## Compatibility, rollout and rollback

- Preserve old field names or return shapes only through explicit temporary compatibility adapters; do not keep two competing sources of truth.
- Add diagnostics for rejected, queued, applied and confirmed states where those are currently conflated.
- Roll out hardware/protocol changes on one test node first and retain a configuration rollback path.
- Update API/OpenAPI/UI/help text in the same change whenever the user-facing contract changes.

## Definition of done

- [ ] All three original verification methods no longer reproduce the defect.
- [ ] No new global state, stale callback, partial persistence or false-success path is introduced.
- [ ] The affected public API/CLI/lifecycle call reports the actual outcome.
- [ ] Complete project suites and focused regression tests pass.
- [ ] Documentation and implementation use one canonical contract.

## Suggested implementation order

1. Add the three focused regression cases.
2. Define the canonical contract/state model.
3. Implement the smallest correction at the owning layer.
4. Migrate direct callers and test doubles.
5. Add failure/restart/concurrency coverage.
6. Run full verification and hardware integration where applicable.
