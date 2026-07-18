# BUG-048 — implementation plan

[← Finding](../../findings/BUG-048-mesh-cli-flood-advert-interval-writes-the-wrong-key.md) · [← Audit index](../../README.md)

> This is a planning document, not a ready-to-apply patch. Revalidate line numbers and surrounding code against the branch being changed.
> Verification status: **three independent checks passed against the supplied snapshots**.

| Field | Value |
|---|---|
| Finding | **Mesh CLI flood advert interval writes a key the scheduler never reads** |
| Classification | **Confirmed defect** |
| Severity | **Medium** |
| Confidence | **Triple-verified** |
| Area | Mesh CLI / advert scheduling |
| Components | OpenHop Repeater |
| Audit date | 2026-07-17 |

## Objective

Eliminate the confirmed contract violation without changing adjacent behavior that is not required by this finding.

## Current behavior

The command writes `flood_advert_interval_hours`, while startup, reload and the timer use `send_advert_interval_hours`. The command persists and displays its own orphan key but cannot change the active periodic advert interval.

## Required outcome

The command must update the canonical scheduler field and report the effective runtime interval.

## Repositories and files to inspect or change

| Repository | Path | Purpose |
|---|---|---|
| OpenHop Repeater | `repeater/handler_helpers/mesh_cli.py` | Confirmed evidence and primary change surface |
| OpenHop Repeater | `repeater/engine.py` | Confirmed evidence and primary change surface |

Before editing, search both repositories for every affected symbol, configuration key, response field and test double. Generated assets and external firmware interfaces must be updated only when they are actual consumers of the corrected contract.

## Implementation work packages

1. Rename the CLI writer/getter to `send_advert_interval_hours`, or migrate all consumers to a single newly named canonical key.
2. Migrate existing orphan values only with explicit precedence rules.
3. Share advert configuration parsing between CLI/API/startup/reload.

## Decisions and assumptions to double-check

- [ ] Determine whether the two names were intended to represent different advert types.
- [ ] Prevent migration from overwriting a valid canonical value with stale orphan data.

## Test plan

### Existing test modules likely to extend

- OpenHop Repeater: `tests/test_handler_helpers_mesh_cli.py`
- OpenHop Repeater: `tests/test_handler_helpers_acl_advert.py`

### Required focused tests

- [ ] Preserve verification method 1: static key trace — CLI writer and runtime reader use different names.
- [ ] Preserve verification method 2: public command persistence — The wrong key becomes 3 while the active key remains 10.
- [ ] Preserve verification method 3: runtime reload — The real reload method ignores the written key.
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
