# BUG-044 — implementation plan

[← Finding](../../findings/BUG-044-mesh-cli-uses-an-obsolete-save-return-contract.md) · [← Audit index](../../README.md)

> This is a planning document, not a ready-to-apply patch. Revalidate line numbers and surrounding code against the branch being changed.
> Verification status: **three independent checks passed against the supplied snapshots**.

| Field | Value |
|---|---|
| Finding | **Mesh CLI uses an obsolete configuration-save return contract** |
| Classification | **Confirmed defect** |
| Severity | **High** |
| Confidence | **Triple-verified** |
| Area | Mesh CLI / persistence contract |
| Components | OpenHop Repeater |
| Audit date | 2026-07-17 |

## Objective

Eliminate the confirmed contract violation without changing adjacent behavior that is not required by this finding.

## Current behavior

Production `ConfigManager.save_to_file()` returns one boolean, while Mesh CLI tuple-unpacks it at 23 call sites. Commands can successfully write the file and then throw `cannot unpack non-iterable bool object`, skip live application, and report an error despite partial success. Existing tests mock the obsolete tuple shape.

## Required outcome

All callers and tests must use one typed save result, with persistence and live-application stages reported consistently.

## Repositories and files to inspect or change

| Repository | Path | Purpose |
|---|---|---|
| OpenHop Repeater | `repeater/config_manager.py` | Confirmed evidence and primary change surface |
| OpenHop Repeater | `repeater/handler_helpers/mesh_cli.py` | Confirmed evidence and primary change surface |
| OpenHop Repeater | `tests/test_handler_helpers_mesh_cli.py` | Confirmed evidence and primary change surface |

Before editing, search both repositories for every affected symbol, configuration key, response field and test double. Generated assets and external firmware interfaces must be updated only when they are actual consumers of the corrected contract.

## Implementation work packages

1. Replace the boolean with a typed `SaveResult` or update every caller to the current boolean contract.
2. Refactor the repeated save/live/reply sequence into one shared Mesh CLI helper.
3. Correct test doubles to use the production signature and add partial-success regression tests.

## Decisions and assumptions to double-check

- [ ] Identify any external/custom ConfigManager implementations still returning tuples.
- [ ] Decide how to report “persisted but live apply failed” without lying or rolling back unexpectedly.

## Test plan

### Existing test modules likely to extend

- OpenHop Repeater: `tests/test_handler_helpers_mesh_cli.py`
- OpenHop Repeater: `tests/test_config_manager.py`

### Required focused tests

- [ ] Preserve verification method 1: static signature/callsites — Production returns bool; Mesh CLI has 23 tuple-unpack sites.
- [ ] Preserve verification method 2: real public command — The file is written, then the command returns a Python error and skips live update.
- [ ] Preserve verification method 3: test-double countercheck — Tests mock a tuple, explaining why the suite does not catch production behavior.
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
