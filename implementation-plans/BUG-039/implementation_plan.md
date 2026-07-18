# BUG-039 — implementation plan

[← Finding](../../findings/BUG-039-frame-server-reconnect-removes-unrelated-push-listeners.md) · [← Audit index](../../README.md)

> This is a planning document, not a ready-to-apply patch. Revalidate line numbers and surrounding code against the branch being changed.
> Verification status: **three independent checks passed against the supplied snapshots**.

| Field | Value |
|---|---|
| Finding | **Frame-server callback setup removes unrelated bridge listeners** |
| Classification | **Confirmed defect** |
| Severity | **High** |
| Confidence | **Triple-verified** |
| Area | Companion callback lifecycle |
| Components | OpenHop Core + OpenHop Repeater |
| Audit date | 2026-07-17 |

## Objective

Eliminate the confirmed contract violation without changing adjacent behavior that is not required by this finding.

## Current behavior

Every frame-server setup invokes bridge-wide `clear_push_callbacks()`, which clears all registered listeners, not only callbacks owned by the prior frame-server client. A reconnect can therefore silently disable separately registered Repeater/API consumers.

## Required outcome

A component must unregister only callbacks it owns; reconnecting one client must not mutate third-party subscriptions.

## Repositories and files to inspect or change

| Repository | Path | Purpose |
|---|---|---|
| OpenHop Core | `src/openhop_core/companion/frame_server/push.py` | Confirmed evidence and primary change surface |
| OpenHop Core | `src/openhop_core/companion/base_callbacks.py` | Confirmed evidence and primary change surface |

Before editing, search both repositories for every affected symbol, configuration key, response field and test double. Generated assets and external firmware interfaces must be updated only when they are actual consumers of the corrected contract.

## Implementation work packages

1. Return registration handles/tokens from callback registration and remove by handle.
2. Have `CompanionFrameServer` retain and replace only its own registrations.
3. Make reconnect setup idempotent without global clearing.

## Decisions and assumptions to double-check

- [ ] Audit all current users of `clear_push_callbacks()` before changing semantics.
- [ ] Define callback lifetime when a frame server object is closed or replaced.

## Test plan

### Existing test modules likely to extend

- OpenHop Core: `tests/test_frame_server.py`
- OpenHop Core: `tests/test_companion_bridge.py`
- OpenHop Repeater: `tests/test_companion_ws_proxy.py`

### Required focused tests

- [ ] Preserve verification method 1: static clear-all trace — Frame setup calls a bridge-wide clear before registering.
- [ ] Preserve verification method 2: third-party listener — An existing listener is removed immediately.
- [ ] Preserve verification method 3: reconnect path — A once-registered external consumer receives no later event after setup runs again.
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
