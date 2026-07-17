# BUG-015 — implementation plan

[← Finding](../../findings/BUG-015-invalid-packets-are-published-to-mqtt-despite-an-explicit-suppression-request.md) · [← Audit index](../../README.md)

> This is a planning document, not a ready-to-apply patch. Revalidate line numbers and surrounding code against the branch being changed.
> Reverification status: **confirmed against the supplied snapshot**.

| Field | Value |
|---|---|
| Finding | **Invalid packets are published to MQTT despite an explicit suppression request** |
| Classification | **Confirmed defect** |
| Severity | **Medium** |
| Confidence | **Confirmed** |
| Area | Packet publication / external telemetry |
| Components | OpenHop Repeater |
| Audit date | 2026-07-17 |

## Objective

Fix the confirmed defect: Storage and local diagnostics may retain invalid packets, but the caller-selected external publication policy must be honored.

## Current behavior to preserve in the reproduction

`record_packet()` documents `skip_mqtt_if_invalid`; `_record_packet_blocking()` passes it to `_publish_packet_sync()`. That method always invokes `_publish_packet_to_mqtt()` regardless of the value. Invalid adverts, empty payloads and overlong paths therefore leak to external MQTT consumers.

## Required outcome

Guard only the MQTT call with `if not skip_mqtt`. Keep Glass/WebSocket behavior explicit rather than overloading the same boolean for every sink.

## Repositories and files to inspect or change

| Repository | Path | Purpose |
|---|---|---|
| OpenHop Repeater | `repeater/engine.py` | Evidence lines 553–576 |
| OpenHop Repeater | `repeater/data_acquisition/storage_collector.py` | Evidence lines 180–240 |

The listed paths are the minimum evidence/change surface identified by the audit. Before editing, search the repositories for the affected symbols, field names and response keys to find indirect consumers, tests and generated artifacts.

## Implementation work packages

1. Replace the inverted/ambiguous MQTT suppression flow with an explicit publication decision at the call site.
2. Guard only MQTT publication when the current behavior intends Glass/WebSocket/storage to continue. Do not reuse one boolean for unrelated sinks.
3. Audit invalid-packet, duplicate-packet and policy-drop paths to ensure each sink receives only the intended records.
4. Add observability for suppressed MQTT publications without logging packet secrets.

## Decisions and assumptions to double-check

- [ ] Map every sink and existing suppression flag before changing behavior.
- [ ] Confirm invalid packets are safe to expose to Glass/WebSocket.
- [ ] Check MQTT retained/QoS behavior is unaffected.

## Test plan

### Existing test modules likely to extend

- OpenHop Repeater: `tests/test_mqtt_publish_integration.py`, `tests/test_storage_collector_ws_stats_throttle.py`
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

- [ ] The behavior described in `BUG-015-invalid-packets-are-published-to-mqtt-despite-an-explicit-suppression-request.md` can no longer be reproduced.
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
