# BUG-034 — implementation plan

[← Finding](../../findings/BUG-034-failed-kiss-config-queueing-still-mutates-local-config.md) · [← Audit index](../../README.md)

> This is a planning document, not a ready-to-apply patch. Revalidate line numbers and surrounding code against the branch being changed.
> Verification status: **three independent checks passed against the supplied snapshots**.

| Field | Value |
|---|---|
| Finding | **Rejected KISS configuration commands still mutate local configuration** |
| Classification | **Confirmed defect** |
| Severity | **Medium** |
| Confidence | **Triple-verified** |
| Area | KISS configuration transaction |
| Components | OpenHop Core |
| Audit date | 2026-07-17 |

## Objective

Eliminate the confirmed contract violation without changing adjacent behavior that is not required by this finding.

## Current behavior

`send_config_command()` updates the adapter’s local configuration before checking TX-buffer capacity. When the queue is full, it returns `False` but leaves local state changed even though the command never reached the TNC.

## Required outcome

Local effective state must change only after the command is accepted, and ideally after the device confirms it.

## Repositories and files to inspect or change

| Repository | Path | Purpose |
|---|---|---|
| OpenHop Core | `src/openhop_core/hardware/kiss_serial_wrapper.py` | Confirmed evidence and primary change surface |

Before editing, search both repositories for every affected symbol, configuration key, response field and test double. Generated assets and external firmware interfaces must be updated only when they are actual consumers of the corrected contract.

## Implementation work packages

1. Validate and encode first, reserve/enqueue capacity, then commit pending/effective state at the correct acknowledgement boundary.
2. Separate requested, pending, and confirmed modem configuration if the protocol can acknowledge settings.
3. Return an explicit result indicating queued versus confirmed.

## Decisions and assumptions to double-check

- [ ] Check whether KISS configuration commands have acknowledgements on all supported modems.
- [ ] Ensure retries do not duplicate state transitions.

## Test plan

### Existing test modules likely to extend

- OpenHop Core: `tests/test_kiss_modem_wrapper.py`

### Required focused tests

- [ ] Preserve verification method 1: static operation order — Local mutation occurs before the queue capacity check.
- [ ] Preserve verification method 2: full queue — The method returns false but the local value changes.
- [ ] Preserve verification method 3: wire-state countercheck — No command frame is added while local state reflects the requested value.
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
