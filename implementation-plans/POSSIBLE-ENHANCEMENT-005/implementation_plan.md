# POSSIBLE-ENHANCEMENT-005 — implementation plan

[← Finding](../../findings/POSSIBLE-ENHANCEMENT-005-define-a-radio-capability-adapter-instead-of-hasattr-branches.md) · [← Audit index](../../README.md)

> This is a planning document, not a ready-to-apply patch. Revalidate line numbers and surrounding code against the branch being changed.
> Reverification status: **factual premise confirmed; implementation remains optional**.

| Field | Value |
|---|---|
| Finding | **Possible enhancement — define a radio capability adapter instead of `hasattr` branches** |
| Classification | **Possible enhancement** |
| Severity | **Enhancement** |
| Confidence | **High** |
| Area | Hardware abstraction |
| Components | OpenHop Core + OpenHop Repeater |
| Audit date | 2026-07-17 |

## Objective

Implement the maintainability improvement without changing unrelated behavior: Define a common `apply_radio_config(snapshot) -> ApplyResult` interface with explicit supported/unsupported fields.

## Current behavior to preserve in the reproduction

`ConfigManager` branches on `configure_radio`, `set_frequency`, `set_tx_power`, `radio_config`, and other optional attributes. Different wrappers apply different subsets.

## Required outcome

Makes partial hardware application impossible to mistake for full success and simplifies ConfigManager.

## Repositories and files to inspect or change

| Repository | Path | Purpose |
|---|---|---|
| OpenHop Repeater | `repeater/config_manager.py` | Evidence lines 76–149 |
| OpenHop Core | `src/openhop_core/hardware/sx1262_wrapper.py` | Evidence lines 1622–1684 |

The listed paths are the minimum evidence/change surface identified by the audit. Before editing, search the repositories for the affected symbols, field names and response keys to find indirect consumers, tests and generated artifacts.

## Implementation work packages

1. Define a radio configuration snapshot and capability/result protocol in Core.
2. Implement the protocol for each hardware wrapper, including explicit unsupported fields and partial-failure reporting.
3. Replace Repeater `hasattr` branches with the protocol and one rollback/restart-required policy.
4. Add hardware-wrapper contract tests shared across implementations.

## Decisions and assumptions to double-check

- [ ] Confirm all existing callers and external contracts before changing the abstraction.
- [ ] Define compatibility and rollback behavior before implementation.
- [ ] Verify that the change does not broaden permissions or expose sensitive data.

## Test plan

### Existing test modules likely to extend

- OpenHop Repeater: `tests/test_config_manager.py`
- OpenHop Repeater: `tests/test_config_manager.py` plus schema/round-trip tests
- OpenHop Core: radio wrapper contract tests; OpenHop Repeater: radio configuration tests

### Required test cases

- [ ] Add characterization tests for the current behavior before refactoring so unrelated semantics cannot change unnoticed.
- [ ] Add a success-path test proving the effective runtime state, persisted state and API/UI-visible state agree after the change where those layers are involved.
- [ ] Add failure-path tests for validation, persistence and live-apply failures where those stages are involved.
- [ ] Run both complete project suites and the audit reproduction checks after the focused tests pass.

### Manual or integration verification

- [ ] Repeat the exact scenario from the finding and record the before/after effective runtime values.
- [ ] Restart the service and verify persisted behavior remains correct where persistence is expected.
- [ ] Exercise a negative/failure path and confirm no partial in-memory or durable state remains.
- [ ] Verify logs and metrics describe the real outcome without reporting success prematurely.

## Compatibility, rollout and rollback

- Implement incrementally behind compatibility adapters; remove the old path only after all callers and tests use the shared abstraction.

- Keep the previous behavior behind a temporary compatibility alias/adapter only when an external contract requires it.
- Make rollback possible without hand-editing corrupted state. Configuration/data migrations need an explicit reverse or safe fallback path.
- Update documentation, OpenAPI/UI text and examples in the same change when user-visible semantics or field names change.

## Definition of done

- [ ] The new shared abstraction has a documented public contract and clear ownership.
- [ ] At least two previously duplicated call sites use the abstraction before legacy code is removed.
- [ ] Behavior remains unchanged except where a linked confirmed defect is intentionally corrected.
- [ ] Tests cover compatibility, migration and failure behavior.

## Suggested implementation order

1. Add or isolate the failing regression test.
2. Introduce the smallest shared model/helper or transaction boundary required by this finding.
3. Migrate the affected runtime path and its direct consumers.
4. Add failure, restart and compatibility tests.
5. Run focused tests, both full project suites, static checks and the audit reproduction checks.
6. Rebuild generated frontend/API artifacts where applicable and verify no stale contract remains.
