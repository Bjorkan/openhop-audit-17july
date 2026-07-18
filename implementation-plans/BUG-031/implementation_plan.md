# BUG-031 — implementation plan

[← Finding](../../findings/BUG-031-kiss-wait-for-rx-completes-an-asyncio-future-from-a-worker-thread.md) · [← Audit index](../../README.md)

> This is a planning document, not a ready-to-apply patch. Revalidate line numbers and surrounding code against the branch being changed.
> Verification status: **three independent checks passed against the supplied snapshots**.

| Field | Value |
|---|---|
| Finding | **KISS wait_for_rx() completes an asyncio future from the serial worker thread** |
| Classification | **Confirmed defect** |
| Severity | **High** |
| Confidence | **Triple-verified** |
| Area | Threading / asyncio interoperability |
| Components | OpenHop Core |
| Audit date | 2026-07-17 |

## Objective

Eliminate the confirmed contract violation without changing adjacent behavior that is not required by this finding.

## Current behavior

The serial RX worker invokes `on_frame_received` synchronously. `wait_for_rx()` temporarily installs a callback that calls `Future.set_result()` directly, crossing from the worker thread into the event loop without `call_soon_threadsafe`. Debug mode raises, and normal mode can leave the waiter asleep until another loop event occurs.

## Required outcome

Worker threads must transfer completion to the owning event loop using its thread-safe scheduling API.

## Repositories and files to inspect or change

| Repository | Path | Purpose |
|---|---|---|
| OpenHop Core | `src/openhop_core/hardware/kiss_serial_wrapper.py` | Confirmed evidence and primary change surface |

Before editing, search both repositories for every affected symbol, configuration key, response field and test double. Generated assets and external firmware interfaces must be updated only when they are actual consumers of the corrected contract.

## Implementation work packages

1. Capture the running loop in `wait_for_rx()` and use `loop.call_soon_threadsafe` to complete the future.
2. Make callback replacement/restoration concurrency-safe and avoid one waiter overwriting a persistent callback.
3. Prefer a thread-safe asyncio queue or a fan-out receive dispatcher for multiple consumers.

## Decisions and assumptions to double-check

- [ ] Verify behavior when the loop closes while the worker is delivering a frame.
- [ ] Decide whether concurrent `wait_for_rx()` calls are supported and enforce the decision.

## Test plan

### Existing test modules likely to extend

- OpenHop Core: `tests/test_kiss_modem_wrapper.py`

### Required focused tests

- [ ] Preserve verification method 1: static thread-hop trace — The worker calls the callback directly and the callback calls `future.set_result` without a thread-safe hop.
- [ ] Preserve verification method 2: debug event loop — Python raises a non-thread-safe event-loop `RuntimeError`.
- [ ] Preserve verification method 3: release-loop wakeup — The waiter does not resume until a separate thread-safe nudge wakes the loop.
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
