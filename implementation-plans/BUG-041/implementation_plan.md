# BUG-041 — implementation plan

[← Finding](../../findings/BUG-041-websocket-restart-can-create-duplicate-heartbeat-threads.md) · [← Audit index](../../README.md)

> This is a planning document, not a ready-to-apply patch. Revalidate line numbers and surrounding code against the branch being changed.
> Verification status: **three independent checks passed against the supplied snapshots**.

| Field | Value |
|---|---|
| Finding | **WebSocket restart can leave duplicate heartbeat threads running** |
| Classification | **Confirmed defect** |
| Severity | **Medium** |
| Confidence | **Triple-verified** |
| Area | WebSocket lifecycle |
| Components | OpenHop Repeater |
| Audit date | 2026-07-17 |

## Objective

Eliminate the confirmed contract violation without changing adjacent behavior that is not required by this finding.

## Current behavior

Shutdown clears a shared boolean and drops the thread reference without joining. If startup sets the same boolean true before the sleeping old loop rechecks it, both old and new threads continue and send heartbeats to the same client set.

## Required outcome

At most one heartbeat worker may exist for a server generation, and shutdown must wait for or permanently invalidate the old worker.

## Repositories and files to inspect or change

| Repository | Path | Purpose |
|---|---|---|
| OpenHop Repeater | `repeater/data_acquisition/websocket_handler.py` | Confirmed evidence and primary change surface |

Before editing, search both repositories for every affected symbol, configuration key, response field and test double. Generated assets and external firmware interfaces must be updated only when they are actual consumers of the corrected contract.

## Implementation work packages

1. Use a per-worker `Event`/generation token rather than one restartable module boolean.
2. Join the old thread outside locks before discarding its reference.
3. Make start/stop serialized and idempotent.

## Decisions and assumptions to double-check

- [ ] Avoid blocking shutdown indefinitely on a stuck client send.
- [ ] Check test/server reload paths that call startup more than once.

## Test plan

### Existing test modules likely to extend

- OpenHop Repeater: `tests/test_api_endpoints_setup.py`

### Required focused tests

- [ ] Preserve verification method 1: static lifecycle trace — Shutdown drops the reference without join; loops share one boolean.
- [ ] Preserve verification method 2: immediate restart — The old thread is alive when the new thread starts, and both remain alive.
- [ ] Preserve verification method 3: observable effect — Both workers send pings to the same client collection.
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
