# BUG-032 — implementation plan

[← Finding](../../findings/BUG-032-meshnode-stop-does-not-stop-the-running-node.md) · [← Audit index](../../README.md)

> This is a planning document, not a ready-to-apply patch. Revalidate line numbers and surrounding code against the branch being changed.
> Verification status: **three independent checks passed against the supplied snapshots**.

| Field | Value |
|---|---|
| Finding | **MeshNode.stop() does not stop a running node** |
| Classification | **Confirmed defect** |
| Severity | **Medium** |
| Confidence | **Triple-verified** |
| Area | Lifecycle / shutdown |
| Components | OpenHop Core |
| Audit date | 2026-07-17 |

## Objective

Eliminate the confirmed contract violation without changing adjacent behavior that is not required by this finding.

## Current behavior

`MeshNode.start()` awaits `Dispatcher.run_forever()`. `MeshNode.stop()` only logs and does not signal, cancel, or await that loop, so callers cannot stop a node through its public lifecycle API.

## Required outcome

After `await node.stop()`, the task created by `node.start()` must terminate and radio/background resources must be closed deterministically.

## Repositories and files to inspect or change

| Repository | Path | Purpose |
|---|---|---|
| OpenHop Core | `src/openhop_core/node/node.py` | Confirmed evidence and primary change surface |
| OpenHop Core | `src/openhop_core/node/dispatcher.py` | Confirmed evidence and primary change surface |

Before editing, search both repositories for every affected symbol, configuration key, response field and test double. Generated assets and external firmware interfaces must be updated only when they are actual consumers of the corrected contract.

## Implementation work packages

1. Add an explicit dispatcher stop event/cancellation contract and have `MeshNode.stop()` invoke and await it.
2. Make start/stop idempotent and define restart support.
3. Close or sleep the radio and cancel owned background tasks during shutdown.

## Decisions and assumptions to double-check

- [ ] Determine ownership: `MeshNode` should not close externally owned resources unless the API documents it.
- [ ] Handle stop calls before start and repeated stop calls.

## Test plan

### Existing test modules likely to extend

- OpenHop Core: `tests/test_mesh_node.py`
- OpenHop Core: `tests/test_dispatcher.py`

### Required focused tests

- [ ] Preserve verification method 1: static lifecycle trace — Start awaits an infinite dispatcher loop; stop only logs.
- [ ] Preserve verification method 2: public stop call — A blocking dispatcher remains active after `await node.stop()`.
- [ ] Preserve verification method 3: real dispatcher loop — The actual `run_forever` task remains pending after stop.
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
