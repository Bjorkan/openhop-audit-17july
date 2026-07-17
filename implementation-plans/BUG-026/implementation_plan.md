# BUG-026 — implementation plan

[← Finding](../../findings/BUG-026-offline-companion-messages-are-dequeued-before-the-response-frame-is-accepted-for-transmission.md) · [← Audit index](../../README.md)

> This is a planning document, not a ready-to-apply patch. Revalidate line numbers and surrounding code against the branch being changed.

| Field | Value |
|---|---|
| Finding | **Offline companion messages are dequeued before the response frame is accepted for transmission** |
| Classification | **Confirmed defect** |
| Severity | **High** |
| Confidence | **Confirmed** |
| Area | Companion offline queue / delivery reliability |
| Components | OpenHop Core + OpenHop Repeater |
| Audit date | 2026-07-17 |

## Objective

Fix the confirmed defect: Offline messages should be removed only after the outbound frame has been accepted, and ideally after transport acknowledgment or connection completion.

## Current behavior to preserve in the reproduction

The command returns no delivery acknowledgment from `_enqueue_frame()`. Once the queue pop or SQLite pop has occurred, a failed enqueue loses the only copy even though the companion never received it.

## Required outcome

Use peek/reserve/commit semantics. Make `_enqueue_frame()` return success, enqueue first, then commit deletion of the reserved in-memory or persisted row.

## Repositories and files to inspect or change

| Repository | Path | Purpose |
|---|---|---|
| OpenHop Core | `src/openhop_core/companion/frame_server/commands_messaging.py` | Evidence lines 430–437 |
| OpenHop Repeater | `repeater/companion/frame_server.py` | Evidence lines 130–138 |
| OpenHop Core | `src/openhop_core/companion/frame_server/transport.py` | Evidence lines 88–113 |

The listed paths are the minimum evidence/change surface identified by the audit. Before editing, search the repositories for the affected symbols, field names and response keys to find indirect consumers, tests and generated artifacts.

## Implementation work packages

1. Add reserve/peek semantics to offline message storage so reading a message does not delete it.
2. Make frame enqueueing return an explicit accepted/rejected result. Commit deletion only after the response frame has been accepted by the transmission queue.
3. Release the reservation on queue-full, encoding, shutdown or transport failure so the message remains available for retry.
4. Define duplicate behavior after process restart and choose an acknowledgement boundary that matches the intended delivery guarantee.

## Decisions and assumptions to double-check

- [ ] Choose acknowledgement boundary carefully: queue acceptance is not radio delivery.
- [ ] Check multiple consumers/reservations.
- [ ] Define stale-reservation recovery.

## Test plan

### Existing test modules likely to extend

- OpenHop Core: `tests/test_companion_stores.py`, `tests/test_companion_bridge.py`
- OpenHop Repeater: `tests/test_companion_message_signal_persistence.py`, `tests/test_companion_advert_persistence.py`

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

- Roll out with delivery/queue metrics enabled and watch retry, duplicate and queue-depth behavior before removing old safeguards.

- Keep the previous behavior behind a temporary compatibility alias/adapter only when an external contract requires it.
- Make rollback possible without hand-editing corrupted state. Configuration/data migrations need an explicit reverse or safe fallback path.
- Update documentation, OpenAPI/UI text and examples in the same change when user-visible semantics or field names change.

## Definition of done

- [ ] The behavior described in `BUG-026-offline-companion-messages-are-dequeued-before-the-response-frame-is-accepted-for-transmission.md` can no longer be reproduced.
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
