# POSSIBLE-ENHANCEMENT-015 — implementation plan

[← Finding](../../findings/POSSIBLE-ENHANCEMENT-015-use-one-callback-invocation-adapter-across-core.md) · [← Audit index](../../README.md)

> This is a planning document, not a ready-to-apply patch. Revalidate line numbers and surrounding code against the branch being changed.
> Reverification status: **factual premise confirmed; implementation remains optional**.

| Field | Value |
|---|---|
| Finding | **Possible enhancement — use one callback invocation adapter across Core** |
| Classification | **Possible enhancement** |
| Severity | **Enhancement** |
| Confidence | **High** |
| Area | Async callback code reuse |
| Components | OpenHop Core |
| Audit date | 2026-07-17 |

## Objective

Implement the maintainability improvement without changing unrelated behavior: One adapter should select a supported signature before invocation, invoke once, await returned awaitables and apply a consistent error policy.

## Current behavior to preserve in the reproduction

Some inspect the function object, one correctly inspects the returned value, and enhanced raw callbacks also implement an exception-based signature fallback.

## Required outcome

Eliminates repeated branches, fixes decorated/callable-object behavior and centralizes callback observability.

## Repositories and files to inspect or change

| Repository | Path | Purpose |
|---|---|---|
| OpenHop Core | `src/openhop_core/node/dispatcher.py` | Evidence lines 1082–1116 |
| OpenHop Core | `src/openhop_core/companion/base_callbacks.py` | Evidence lines 44–50 |
| OpenHop Core | `src/openhop_core/callbacks.py` (new or consolidated) | Proposed shared callback adapter; exact module placement must follow Core package ownership |


The listed paths are the minimum evidence/change surface identified by the audit. Before editing, search the repositories for the affected symbols, field names and response keys to find indirect consumers, tests and generated artifacts.

## Implementation work packages

1. Implement one callback adapter that selects arguments, invokes once, awaits awaitables and records failures.
2. Adopt it across Core callback sites and remove duplicate introspection/event-loop code.
3. Specify callback ordering, cancellation and exception-isolation guarantees.
4. Test diverse callable forms and both sync/async returns.

## Decisions and assumptions to double-check

- [ ] Confirm all existing callers and external contracts before changing the abstraction.
- [ ] Define compatibility and rollback behavior before implementation.
- [ ] Verify that the change does not broaden permissions or expose sensitive data.

## Test plan

### Existing test modules likely to extend

- OpenHop Repeater: `tests/test_packet_router.py`; OpenHop Core companion tests where applicable
- OpenHop Core: callback/dispatcher/handler tests

### Required test cases

- [ ] Add characterization tests for the current behavior before refactoring so unrelated semantics cannot change unnoticed.
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
