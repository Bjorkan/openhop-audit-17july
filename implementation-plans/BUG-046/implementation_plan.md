# BUG-046 — implementation plan

[← Finding](../../findings/BUG-046-mesh-cli-frequency-command-stores-mhz-as-hz.md) · [← Audit index](../../README.md)

> This is a planning document, not a ready-to-apply patch. Revalidate line numbers and surrounding code against the branch being changed.
> Verification status: **three independent checks passed against the supplied snapshots**.

| Field | Value |
|---|---|
| Finding | **Mesh CLI documents frequency in MHz but stores the value as Hz** |
| Classification | **Confirmed defect** |
| Severity | **High** |
| Confidence | **Triple-verified** |
| Area | Mesh CLI / radio units |
| Components | OpenHop Repeater |
| Audit date | 2026-07-17 |

## Objective

Eliminate the confirmed contract violation without changing adjacent behavior that is not required by this finding.

## Current behavior

The CLI help says `set freq <mhz>` and the getter converts stored Hz to MHz, but the setter stores the raw decimal token in the Hz field. `869.618` is persisted as `869.618` and live application truncates it to `869` Hz.

## Required outcome

The setter must convert MHz to integer Hz with validation before persistence and hardware application.

## Repositories and files to inspect or change

| Repository | Path | Purpose |
|---|---|---|
| OpenHop Repeater | `repeater/handler_helpers/mesh_cli.py` | Confirmed evidence and primary change surface |
| OpenHop Repeater | `repeater/config_manager.py` | Confirmed evidence and primary change surface |

Before editing, search both repositories for every affected symbol, configuration key, response field and test double. Generated assets and external firmware interfaces must be updated only when they are actual consumers of the corrected contract.

## Implementation work packages

1. Parse with `Decimal` or a clearly documented numeric conversion and multiply by 1,000,000.
2. Validate the resulting frequency against the supported regional/radio range before mutating configuration.
3. Use a shared frequency parser/formatter for CLI, API and configuration.

## Decisions and assumptions to double-check

- [ ] Define rounding behavior for sub-Hz decimals.
- [ ] Check whether any scripts have worked around the bug by passing raw Hz despite the documented MHz contract.

## Test plan

### Existing test modules likely to extend

- OpenHop Repeater: `tests/test_handler_helpers_mesh_cli.py`
- OpenHop Repeater: `tests/test_config_manager.py`
- OpenHop Repeater: `tests/test_config_radio.py`

### Required focused tests

- [ ] Preserve verification method 1: static help/getter/setter trace — Help/get use MHz, setter writes raw value.
- [ ] Preserve verification method 2: public command persistence — `869.618` is stored unchanged in the frequency field.
- [ ] Preserve verification method 3: live application — ConfigManager converts the stored value to integer 869 and applies it as Hz.
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
