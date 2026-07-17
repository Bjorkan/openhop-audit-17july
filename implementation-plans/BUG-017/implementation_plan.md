# BUG-017 — implementation plan

[← Finding](../../findings/BUG-017-live-reload-can-silently-reduce-the-packet-deduplication-window-from-one-hour-to-one-minute.md) · [← Audit index](../../README.md)

> This is a planning document, not a ready-to-apply patch. Revalidate line numbers and surrounding code against the branch being changed.

| Field | Value |
|---|---|
| Finding | **Live reload can silently reduce the packet deduplication window from one hour to one minute** |
| Classification | **Confirmed defect** |
| Severity | **High** |
| Confidence | **Confirmed** |
| Area | Runtime configuration / packet deduplication |
| Components | OpenHop Repeater |
| Audit date | 2026-07-17 |

## Objective

Fix the confirmed defect: Initialization and reload must use the same parser, defaults and bounds.

## Current behavior to preserve in the reproduction

Any live update that reloads the `repeater` section can change a running instance from one-hour deduplication to one minute when `cache_ttl` is absent. Configured values below five minutes are rejected at startup by clamping but accepted during reload. The same configuration therefore has different semantics before and after an unrelated live change.

## Required outcome

Create one `parse_runtime_repeater_settings()` function and assign its immutable result at startup and reload. Preserve the five-minute minimum and 3,600-second default.

## Repositories and files to inspect or change

| Repository | Path | Purpose |
|---|---|---|
| OpenHop Repeater | `repeater/engine.py` | Evidence lines 124–137 |
| OpenHop Repeater | `repeater/config_manager.py` | Evidence lines 286–307 |

The listed paths are the minimum evidence/change surface identified by the audit. Before editing, search the repositories for the affected symbols, field names and response keys to find indirect consumers, tests and generated artifacts.

## Implementation work packages

1. Create one parser for runtime repeater settings and use it during startup and every live reload.
2. Centralize defaults, minimums, maximums, unit conversion and legacy-key migration. Preserve the intended 3,600-second default and five-minute minimum for deduplication.
3. Replace field-by-field reload assignments with atomic replacement of a validated settings snapshot.
4. Emit a warning when an invalid value is rejected instead of silently falling back to a different default.

## Decisions and assumptions to double-check

- [ ] Compare every startup assignment with reload assignment.
- [ ] Confirm default/minimum values from docs and config example.
- [ ] Check changing cache TTL does not invalidate entries incorrectly.

## Test plan

### Existing test modules likely to extend

- OpenHop Repeater: `tests/test_config_manager.py`
- OpenHop Repeater: `tests/test_engine.py`, `tests/test_flood_loop_dedup.py`

### Required test cases

- [ ] Add a focused regression test that reproduces the current defect before the implementation and fails for the documented reason.
- [ ] Add a success-path test proving the effective runtime state, persisted state and API/UI-visible state agree after the change where those layers are involved.
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

- [ ] The behavior described in `BUG-017-live-reload-can-silently-reduce-the-packet-deduplication-window-from-one-hour-to-one-minute.md` can no longer be reproduced.
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
