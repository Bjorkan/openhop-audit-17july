# BUG-029 — implementation plan

[← Finding](../../findings/BUG-029-successful-kiss-queueing-is-reported-as-send-failure.md) · [← Audit index](../../README.md)

> This is a planning document, not a ready-to-apply patch. Revalidate line numbers and surrounding code against the branch being changed.
> Verification status: **three independent checks passed against the supplied snapshots**.

| Field | Value |
|---|---|
| Finding | **Successful KISS queueing is reported as a transmission failure** |
| Classification | **Confirmed defect** |
| Severity | **Medium** |
| Confidence | **Triple-verified** |
| Area | Transmission result contract |
| Components | OpenHop Core |
| Audit date | 2026-07-17 |

## Objective

Eliminate the confirmed contract violation without changing adjacent behavior that is not required by this finding.

## Current behavior

The abstract radio contract permits a successful send to return `None`, and the KISS adapter does exactly that after accepting a frame. `Dispatcher` interprets the same `None` as failure, returns `False`, and skips successful-send callbacks even though the frame is queued for transmission.

## Required outcome

A successful transport submission must have one unambiguous result shared by all radio implementations and `Dispatcher`.

## Repositories and files to inspect or change

| Repository | Path | Purpose |
|---|---|---|
| OpenHop Core | `src/openhop_core/hardware/base.py` | Confirmed evidence and primary change surface |
| OpenHop Core | `src/openhop_core/hardware/kiss_serial_wrapper.py` | Confirmed evidence and primary change surface |
| OpenHop Core | `src/openhop_core/node/dispatcher.py` | Confirmed evidence and primary change surface |

Before editing, search both repositories for every affected symbol, configuration key, response field and test double. Generated assets and external firmware interfaces must be updated only when they are actual consumers of the corrected contract.

## Implementation work packages

1. Replace the ambiguous `dict | None` result with a typed result carrying success plus optional metadata, or make every successful adapter return a metadata mapping.
2. Update KISS and all other radio implementations atomically with the dispatcher interpretation.
3. Ensure sent callbacks and accounting execute exactly once after an accepted submission.

## Decisions and assumptions to double-check

- [ ] Decide whether success means queued, written to transport, or confirmed by hardware; document that boundary.
- [ ] Check callers that currently use `None` to mean both “success without metadata” and “failure”.

## Test plan

### Existing test modules likely to extend

- OpenHop Core: `tests/test_dispatcher.py`
- OpenHop Core: `tests/test_kiss_modem_wrapper.py`

### Required focused tests

- [ ] Preserve verification method 1: static contract contradiction — The base contract and KISS docstring permit/return `None`; Dispatcher rejects `None`.
- [ ] Preserve verification method 2: direct adapter path — KISS accepts the frame and returns `None` without raising.
- [ ] Preserve verification method 3: dispatcher integration — The same accepted frame produces `False` from `send_packet`.
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
