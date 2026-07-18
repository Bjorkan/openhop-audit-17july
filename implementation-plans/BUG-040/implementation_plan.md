# BUG-040 — implementation plan

[← Finding](../../findings/BUG-040-companion-preference-save-failures-are-reported-as-success.md) · [← Audit index](../../README.md)

> This is a planning document, not a ready-to-apply patch. Revalidate line numbers and surrounding code against the branch being changed.
> Verification status: **three independent checks passed against the supplied snapshots**.

| Field | Value |
|---|---|
| Finding | **Companion preference save failures are reported as successful runtime changes** |
| Classification | **Confirmed defect** |
| Severity | **Medium** |
| Confidence | **Triple-verified** |
| Area | Companion preference persistence |
| Components | OpenHop Repeater |
| Audit date | 2026-07-17 |

## Objective

Eliminate the confirmed contract violation without changing adjacent behavior that is not required by this finding.

## Current behavior

`RepeaterCompanionBridge._save_prefs()` ignores the SQLite handler’s boolean result. Public setters mutate runtime preferences and return normally even when persistence fails, so a restart silently restores the old value.

## Required outcome

Setters must report persistence failure and either roll back runtime state or explicitly expose a volatile-only result.

## Repositories and files to inspect or change

| Repository | Path | Purpose |
|---|---|---|
| OpenHop Repeater | `repeater/companion/bridge.py` | Confirmed evidence and primary change surface |
| OpenHop Core | `src/openhop_core/companion/base_config.py` | Confirmed evidence and primary change surface |

Before editing, search both repositories for every affected symbol, configuration key, response field and test double. Generated assets and external firmware interfaces must be updated only when they are actual consumers of the corrected contract.

## Implementation work packages

1. Make `_save_prefs()` return/raise a typed result and propagate it to all preference setters and API callers.
2. Stage the new preference, persist it, then commit runtime state; roll back on failure.
3. Log and expose the actual durable/effective state.

## Decisions and assumptions to double-check

- [ ] Audit whether any callers intentionally want non-durable changes.
- [ ] Handle SQLite exceptions and false returns consistently.

## Test plan

### Existing test modules likely to extend

- OpenHop Repeater: `tests/test_companion_bridge_prefs.py`
- OpenHop Repeater: `tests/test_companion_settings.py`
- OpenHop Repeater: `tests/test_companion_state_load.py`

### Required focused tests

- [ ] Preserve verification method 1: static return discard — The persistence method returns bool but `_save_prefs` ignores it.
- [ ] Preserve verification method 2: failed setter — The setter returns normally and mutates runtime state after an explicit false save.
- [ ] Preserve verification method 3: restart countercheck — A fresh bridge loads the old persisted value.
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
