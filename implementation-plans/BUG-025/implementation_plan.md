# BUG-025 — implementation plan

[← Finding](../../findings/BUG-025-callbacks-returning-awaitables-from-synchronous-wrappers-are-silently-not-awaited.md) · [← Audit index](../../README.md)

> This is a planning document, not a ready-to-apply patch. Revalidate line numbers and surrounding code against the branch being changed.
> Reverification status: **confirmed against the supplied snapshot**.

| Field | Value |
|---|---|
| Finding | **Callbacks returning awaitables from synchronous wrappers are silently not awaited** |
| Classification | **Confirmed defect** |
| Severity | **Medium** |
| Confidence | **Confirmed** |
| Area | Callback dispatch / async interoperability |
| Components | OpenHop Core |
| Audit date | 2026-07-17 |

## Objective

Fix the confirmed defect: Callback invocation should always call once, inspect the returned object and await it when `inspect.isawaitable(result)` is true.

## Current behavior to preserve in the reproduction

This affects callable objects with async `__call__`, decorated async functions whose wrapper is synchronous, sync wrappers and callable objects and intentionally synchronous adapters returning a coroutine. Type annotations allow `Awaitable | None`, and another helper in the same module already implements the correct “call, then inspect result” pattern.

## Required outcome

Introduce one shared `_invoke_maybe_awaitable(callback, *args)` helper and use it in Dispatcher, ACK/login handlers and Companion callback dispatch.

## Repositories and files to inspect or change

| Repository | Path | Purpose |
|---|---|---|
| OpenHop Core | `src/openhop_core/node/dispatcher.py` | Evidence lines 325–363 |
| OpenHop Core | `src/openhop_core/companion/base_callbacks.py` | Evidence lines 44–50 |

The listed paths are the minimum evidence/change surface identified by the audit. Before editing, search the repositories for the affected symbols, field names and response keys to find indirect consumers, tests and generated artifacts.

## Implementation work packages

1. Create one callback invocation adapter that calls the selected signature and awaits any `inspect.isawaitable()` result.
2. Use the adapter in Dispatcher, ACK/login handling and Companion callback dispatch instead of maintaining independent sync/async branches.
3. Define scheduling semantics when the caller itself is synchronous; either make the path async or explicitly schedule on the owning event loop and surface failures.
4. Add logging for callback failures and ensure no un-awaited coroutine warnings remain.

## Decisions and assumptions to double-check

- [ ] Define event-loop ownership for sync callers.
- [ ] Ensure callback exceptions are observed.
- [ ] Check cancellation does not leak tasks.

## Test plan

### Existing test modules likely to extend

- OpenHop Core: `tests/test_dispatcher.py`, `tests/test_handlers.py`, `tests/test_events.py`

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

- [ ] The behavior described in `BUG-025-callbacks-returning-awaitables-from-synchronous-wrappers-are-silently-not-awaited.md` can no longer be reproduced.
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
