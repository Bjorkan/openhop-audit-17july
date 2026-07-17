# BUG-027 — implementation plan

[← Finding](../../findings/BUG-027-concurrent-message-persistence-can-remove-a-different-newer-message-from-memory.md) · [← Audit index](../../README.md)

> This is a planning document, not a ready-to-apply patch. Revalidate line numbers and surrounding code against the branch being changed.
> Reverification status: **confirmed against the supplied snapshot**.

| Field | Value |
|---|---|
| Finding | **Concurrent message persistence can remove a different, newer message from memory** |
| Classification | **Confirmed defect** |
| Severity | **High** |
| Confidence | **Confirmed** |
| Area | Companion persistence / concurrency |
| Components | OpenHop Core + OpenHop Repeater |
| Audit date | 2026-07-17 |

## Objective

Fix the confirmed defect: Persistence completion must remove the exact queue entry associated with that operation, independent of interleaving pushes.

## Current behavior to preserve in the reproduction

While `_persist_companion_message()` awaits `asyncio.to_thread()`, another packet task can push a newer message. On success, `pop_last()` removes that newer message. The older persisted message remains in memory, causing a duplicate later, while the newer unpersisted message is lost.

## Required outcome

Assign queue entry IDs/tokens and remove by identity after successful persistence. Better, make the queue/persistence layer one transactional outbox with serialized ownership.

## Repositories and files to inspect or change

| Repository | Path | Purpose |
|---|---|---|
| OpenHop Repeater | `repeater/companion/frame_server.py` | Evidence lines 69–99 |
| OpenHop Core | `src/openhop_core/companion/message_queue.py` | Evidence lines 32–61 |
| OpenHop Core | `src/openhop_core/companion/base_events.py` | Verify queue insertion and persistence callback ordering |

The listed paths are the minimum evidence/change surface identified by the audit. Before editing, search the repositories for the affected symbols, field names and response keys to find indirect consumers, tests and generated artifacts.

## Implementation work packages

1. Give every in-memory queue entry a stable identity/token at insertion time; duplicate payloads must still receive distinct identities.
2. Pass that identity through `MessageEvent` / `ChannelMessageEvent` persistence callbacks and remove exactly that entry after successful durable write; never remove by current queue position.
3. Serialize mutation or protect the queue/index with the appropriate lock so producer and persistence completion cannot race.
4. Consider consolidating memory and SQLite into a transactional outbox to avoid two sources of truth.

## Decisions and assumptions to double-check

- [ ] Duplicate payloads must remain distinguishable.
- [ ] Check SQLite callback ordering and shutdown.
- [ ] Avoid O(n) scans under sustained queue load if possible.

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

- [ ] The behavior described in `BUG-027-concurrent-message-persistence-can-remove-a-different-newer-message-from-memory.md` can no longer be reproduced.
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
