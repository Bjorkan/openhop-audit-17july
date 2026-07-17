# POSSIBLE-ENHANCEMENT-014 — implementation plan

[← Finding](../../findings/POSSIBLE-ENHANCEMENT-014-replace-publication-booleans-with-a-typed-sink-policy.md) · [← Audit index](../../README.md)

> This is a planning document, not a ready-to-apply patch. Revalidate line numbers and surrounding code against the branch being changed.
> Reverification status: **factual premise confirmed; implementation remains optional**.

| Field | Value |
|---|---|
| Finding | **Possible enhancement — replace publication booleans with a typed sink policy** |
| Classification | **Possible enhancement** |
| Severity | **Enhancement** |
| Confidence | **High** |
| Area | Telemetry architecture |
| Components | OpenHop Repeater |
| Audit date | 2026-07-17 |

## Objective

Implement the maintainability improvement without changing unrelated behavior: Pass a typed publication policy such as `PublicationTargets(storage=True, glass=True, websocket=True, mqtt=False)`.

## Current behavior to preserve in the reproduction

A negative boolean with conditional semantics is easy to ignore and does not explain whether invalid records should reach each individual sink.

## Required outcome

Makes each sink decision explicit, avoids inverted flags and simplifies tests for invalid, duplicate and operational-drop records.

## Repositories and files to inspect or change

| Repository | Path | Purpose |
|---|---|---|
| OpenHop Repeater | `repeater/engine.py` | Evidence lines 553–576 |
| OpenHop Repeater | `repeater/data_acquisition/storage_collector.py` | Evidence lines 180–240 |

The listed paths are the minimum evidence/change surface identified by the audit. Before editing, search the repositories for the affected symbols, field names and response keys to find indirect consumers, tests and generated artifacts.

## Implementation work packages

1. Replace inverted booleans with a `PublicationTargets`/sink-policy value object.
2. Make each packet classification choose explicit targets and pass them to storage/publication code.
3. Add per-sink counters and structured reasons for suppression.
4. Test invalid, duplicate, local-only and normal records across every sink.

## Decisions and assumptions to double-check

- [ ] Confirm all existing callers and external contracts before changing the abstraction.
- [ ] Define compatibility and rollback behavior before implementation.
- [ ] Verify that the change does not broaden permissions or expose sensitive data.

## Test plan

### Existing test modules likely to extend

- OpenHop Repeater: `tests/test_mqtt_publish_integration.py`, `tests/test_storage_collector_ws_stats_throttle.py`
- OpenHop Repeater: `tests/test_engine.py`, `tests/test_flood_loop_dedup.py`
- OpenHop Repeater: storage/MQTT integration and overload tests

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
