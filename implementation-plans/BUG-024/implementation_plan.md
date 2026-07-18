# BUG-024 — implementation plan

[← Finding](../../findings/BUG-024-an-enhanced-raw-callback-is-invoked-twice-when-its-handler-raises.md) · [← Audit index](../../README.md)

> This is a planning document, not a ready-to-apply patch. Revalidate line numbers and surrounding code against the branch being changed.
> Reverification status: **confirmed against the supplied snapshot**.

| Field | Value |
|---|---|
| Finding | **An enhanced raw callback is invoked twice when its handler raises** |
| Classification | **Confirmed defect** |
| Severity | **Medium** |
| Confidence | **Confirmed** |
| Area | Callback dispatch / side effects |
| Components | OpenHop Core |
| Audit date | 2026-07-17 |

## Objective

Fix the confirmed defect: Signature compatibility should be resolved before invocation. A runtime exception from the chosen callback form must be reported once, not interpreted as arity mismatch.

## Current behavior to preserve in the reproduction

A valid enhanced callback may store data, increment counters or enqueue work and then raise. Dispatcher logs the failure and calls it again with two arguments. Side effects can be duplicated, and the second call can execute a different compatibility branch inside variadic callbacks.

## Required outcome

Inspect/bind the callable signature before the call, or register callback capability explicitly. Invoke exactly once and separately catch handler errors.

## Repositories and files to inspect or change

| Repository | Path | Purpose |
|---|---|---|
| OpenHop Core | `src/openhop_core/node/dispatcher.py` | Evidence lines 1082–1116 |

The listed paths are the minimum evidence/change surface identified by the audit. Before editing, search the repositories for the affected symbols, field names and response keys to find indirect consumers, tests and generated artifacts.

## Implementation work packages

1. Select the compatible callback signature before invocation using `inspect.signature().bind()` or explicit registration metadata.
2. Invoke the callback exactly once. Catch signature-selection errors separately from exceptions raised inside the callback.
3. Preserve the original handler exception for logging/metrics without attempting a fallback invocation that repeats side effects.
4. Test functions, bound methods, decorated callables, partials and callable objects.

## Decisions and assumptions to double-check

- [ ] Decorators may hide signatures; use `inspect.unwrap` where safe.
- [ ] Do not classify handler `TypeError` as argument mismatch.
- [ ] Check callback ordering and retry semantics.

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

- [ ] The behavior described in `BUG-024-an-enhanced-raw-callback-is-invoked-twice-when-its-handler-raises.md` can no longer be reproduced.
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
