# BUG-016 — implementation plan

[← Finding](../../findings/BUG-016-the-raw-duplicate-path-bypasses-the-configured-per-packet-duplicate-cap.md) · [← Audit index](../../README.md)

> This is a planning document, not a ready-to-apply patch. Revalidate line numbers and surrounding code against the branch being changed.

| Field | Value |
|---|---|
| Finding | **The raw duplicate path bypasses the configured per-packet duplicate cap** |
| Classification | **Confirmed defect** |
| Severity | **Medium** |
| Confidence | **Confirmed** |
| Area | Packet history / memory bounds |
| Components | OpenHop Repeater |
| Audit date | 2026-07-17 |

## Objective

Fix the confirmed defect: Every entry path that groups duplicates under an original must apply the same cap and accounting semantics.

## Current behavior to preserve in the reproduction

The raw RX path exists specifically for duplicates filtered before the normal engine path. Its grouping logic duplicates the normal branch but omits the `max_duplicates_per_packet` check, so a persistent duplicate storm can grow one recent-packet record without bound until that parent record ages out.

## Required outcome

Extract `_attach_duplicate_or_append(record)` and use it from both paths. Optionally track a `duplicates_omitted` counter after the cap.

## Repositories and files to inspect or change

| Repository | Path | Purpose |
|---|---|---|
| OpenHop Repeater | `repeater/engine.py` | Evidence lines 124–137 |

The listed paths are the minimum evidence/change surface identified by the audit. Before editing, search the repositories for the affected symbols, field names and response keys to find indirect consumers, tests and generated artifacts.

## Implementation work packages

1. Extract one duplicate-grouping function that owns matching, append behavior, per-packet cap enforcement and omitted-count metadata.
2. Call the helper from both normal and raw packet paths; remove duplicated branches rather than fixing only one copy.
3. Specify whether the cap counts the original record, duplicate records only, or total observations, and make UI terminology match.
4. Keep memory bounded when duplicate input is sustained for long periods.

## Decisions and assumptions to double-check

- [ ] Confirm cap semantics and UI expectations.
- [ ] Check records loaded from persistence use the same grouping path.
- [ ] Ensure omitted duplicates do not break last-seen/RSSI summaries.

## Test plan

### Existing test modules likely to extend

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

- [ ] The behavior described in `BUG-016-the-raw-duplicate-path-bypasses-the-configured-per-packet-duplicate-cap.md` can no longer be reproduced.
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
