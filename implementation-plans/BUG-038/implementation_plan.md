# BUG-038 — implementation plan

[← Finding](../../findings/BUG-038-login-responses-use-one-global-unkeyed-slot.md) · [← Audit index](../../README.md)

> This is a planning document, not a ready-to-apply patch. Revalidate line numbers and surrounding code against the branch being changed.
> Verification status: **three independent checks passed against the supplied snapshots**.

| Field | Value |
|---|---|
| Finding | **Companion login responses use one global completion slot** |
| Classification | **Confirmed defect** |
| Severity | **High** |
| Confidence | **Triple-verified** |
| Area | Companion login correlation |
| Components | OpenHop Core |
| Audit date | 2026-07-17 |

## Objective

Eliminate the confirmed contract violation without changing adjacent behavior that is not required by this finding.

## Current behavior

Login passwords are tracked per destination hash, but completion uses one globally replaced callback. Concurrent logins can resolve the newer request with data from the older peer, and cleanup from an older request can clear the newer callback.

## Required outcome

Login completion and cleanup must be scoped to the exact destination/request that created the waiter.

## Repositories and files to inspect or change

| Repository | Path | Purpose |
|---|---|---|
| OpenHop Core | `src/openhop_core/companion/base_send.py` | Confirmed evidence and primary change surface |
| OpenHop Core | `src/openhop_core/node/handlers/login_response.py` | Confirmed evidence and primary change surface |

Before editing, search both repositories for every affected symbol, configuration key, response field and test double. Generated assets and external firmware interfaces must be updated only when they are actual consumers of the corrected contract.

## Implementation work packages

1. Replace the global login callback with a pending-request map keyed by destination hash and request generation/token.
2. Dispatch a verified response directly to its matching waiter.
3. Make timeout/cancellation remove only its own entry.

## Decisions and assumptions to double-check

- [ ] Confirm collision handling when destination hashes are truncated.
- [ ] Ensure authentication state and password cleanup remain isolated per peer.

## Test plan

### Existing test modules likely to extend

- OpenHop Core: `tests/test_companion_bridge.py`
- OpenHop Core: `tests/test_companion_base.py`

### Required focused tests

- [ ] Preserve verification method 1: static state mismatch — Passwords are keyed, but the completion callback is global.
- [ ] Preserve verification method 2: overlapping login — Response data for A resolves B while A remains pending.
- [ ] Preserve verification method 3: cleanup interference — Cancellation/cleanup of an older login clears the newer waiter.
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
