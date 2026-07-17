# BUG-018 — implementation plan

[← Finding](../../findings/BUG-018-deep-update-nested-replaces-sibling-configuration-instead-of-updating-one-value.md) · [← Audit index](../../README.md)

> This is a planning document, not a ready-to-apply patch. Revalidate line numbers and surrounding code against the branch being changed.
> Reverification status: **confirmed against the supplied snapshot**.

| Field | Value |
|---|---|
| Finding | **`update_nested()` replaces sibling configuration instead of updating one deep value** |
| Classification | **Confirmed defect** |
| Severity | **Low** |
| Confidence | **Confirmed** |
| Area | Configuration helper semantics |
| Components | OpenHop Repeater |
| Audit date | 2026-07-17 |

## Objective

Fix the confirmed defect: A dotted-path update must modify exactly the named leaf and preserve unrelated siblings.

## Current behavior to preserve in the reproduction

For `repeater.security.admin_password`, `update_nested()` constructs `{repeater: {security: {admin_password: ...}}}`. `update_and_save()` then performs `config["repeater"].update(...)`, replacing all of `security`; JWT secrets, guest credentials or other sibling keys disappear.

## Required outcome

Traverse a copied config to the target leaf, assign there, and commit transactionally. Alternatively make `update_and_save()` perform a documented recursive merge, with explicit replacement markers for callers that need replacement.

## Repositories and files to inspect or change

| Repository | Path | Purpose |
|---|---|---|
| OpenHop Repeater | `repeater/config_manager.py` | Evidence lines 385–417 |

The listed paths are the minimum evidence/change surface identified by the audit. Before editing, search the repositories for the affected symbols, field names and response keys to find indirect consumers, tests and generated artifacts.

## Implementation work packages

1. Define and document whether nested updates are leaf assignment, recursive merge or section replacement. The current helper name should not conceal replacement semantics.
2. Implement traversal on a copied configuration, create missing dictionaries deliberately, and assign only the target leaf for leaf-update calls.
3. Provide a separate explicit replacement API for callers that intentionally replace a whole section.
4. Commit through the transactional configuration path and preserve sibling keys on validation/save failure.

## Decisions and assumptions to double-check

- [ ] Inventory callers that may rely on replacement behavior.
- [ ] Define behavior when an intermediate path is non-dictionary.
- [ ] Check list values and deletion semantics.

## Test plan

### Existing test modules likely to extend

- OpenHop Repeater: `tests/test_config_manager.py`

### Required test cases

- [ ] Add a focused regression test that reproduces the current defect before the implementation and fails for the documented reason.
- [ ] Add a success-path test proving the effective runtime state, persisted state and API/UI-visible state agree after the change where those layers are involved.
- [ ] Add deterministic ordering/race tests using barriers or fake executors; do not rely on timing sleeps.
- [ ] Add failure-path tests for validation, persistence and live-apply failures where those stages are involved.
- [ ] Run both complete project suites and the audit reproduction checks after the focused tests pass.

### Manual or integration verification

- [ ] Repeat the exact scenario from the finding and record the before/after effective runtime values.
- [ ] Restart the service and verify persisted behavior remains correct where persistence is expected.
- [ ] Exercise a negative/failure path and confirm no partial in-memory or durable state remains.
- [ ] Verify logs and metrics describe the real outcome without reporting success prematurely.

## Compatibility, rollout and rollback

- No special deployment note beyond the repository’s normal staged rollout and rollback process.

- Keep the previous behavior behind a temporary compatibility alias/adapter only when an external contract requires it.
- Make rollback possible without hand-editing corrupted state. Configuration/data migrations need an explicit reverse or safe fallback path.
- Update documentation, OpenAPI/UI text and examples in the same change when user-visible semantics or field names change.

## Definition of done

- [ ] The behavior described in `BUG-018-deep-update-nested-replaces-sibling-configuration-instead-of-updating-one-value.md` can no longer be reproduced.
- [ ] Runtime behavior, persisted configuration/queue state and API/UI telemetry agree for the affected operation.
- [ ] Failure paths return an explicit failure or restart-required result and do not silently commit partial state.
- [ ] A regression test fails on the supplied snapshot and passes with the implementation.

## Suggested implementation order

1. Add or isolate the failing regression test.
2. Introduce the smallest shared model/helper or transaction boundary required by this finding.
3. Migrate the affected runtime path and its direct consumers.
4. Add failure, restart and compatibility tests.
5. Run focused tests, both full project suites, static checks and the audit reproduction checks.
6. Rebuild generated frontend/API artifacts where applicable and verify no stale contract remains.
