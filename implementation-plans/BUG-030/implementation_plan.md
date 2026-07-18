# BUG-030 — implementation plan

[← Finding](../../findings/BUG-030-unterminated-kiss-rx-frames-grow-without-bound.md) · [← Audit index](../../README.md)

> This is a planning document, not a ready-to-apply patch. Revalidate line numbers and surrounding code against the branch being changed.
> Verification status: **three independent checks passed against the supplied snapshots**.

| Field | Value |
|---|---|
| Finding | **Unterminated KISS receive frames can grow memory without bound** |
| Classification | **Confirmed defect** |
| Severity | **High** |
| Confidence | **Triple-verified** |
| Area | KISS parser / memory safety |
| Components | OpenHop Core |
| Audit date | 2026-07-17 |

## Objective

Eliminate the confirmed contract violation without changing adjacent behavior that is not required by this finding.

## Current behavior

`MAX_FRAME_SIZE` constrains transmitted frames, but neither receive decoder enforces it. A stream that starts a KISS frame and never terminates it continuously appends to `rx_frame_buffer`, allowing malformed input or a noisy serial link to consume unbounded memory.

## Required outcome

Receive parsing must cap frame size, increment an error metric, discard/resynchronize safely, and continue processing subsequent valid frames.

## Repositories and files to inspect or change

| Repository | Path | Purpose |
|---|---|---|
| OpenHop Core | `src/openhop_core/hardware/kiss_serial_wrapper.py` | Confirmed evidence and primary change surface |

Before editing, search both repositories for every affected symbol, configuration key, response field and test double. Generated assets and external firmware interfaces must be updated only when they are actual consumers of the corrected contract.

## Implementation work packages

1. Enforce a receive-frame bound in the shared byte-processing path used by both decoder entry points.
2. On overflow, increment a dedicated/error counter, clear parser state, and wait for the next frame delimiter.
3. Keep escaped-byte and port-command parsing correct after resynchronization.

## Decisions and assumptions to double-check

- [ ] Confirm the maximum legal payload including KISS command/port bytes and escaping expansion.
- [ ] Choose whether oversized frames are dropped immediately or drained until the next delimiter.

## Test plan

### Existing test modules likely to extend

- OpenHop Core: `tests/test_kiss_modem_wrapper.py`

### Required focused tests

- [ ] Preserve verification method 1: bytewise decoder — A frame reached 10,240 bytes with a configured maximum of 512.
- [ ] Preserve verification method 2: bulk decoder — One chunk produced a 51,200-byte receive buffer.
- [ ] Preserve verification method 3: worker-like stream — Repeated 4 KiB chunks grew the buffer to 131,072 bytes without a terminator.
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
