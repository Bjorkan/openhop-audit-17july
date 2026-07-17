# BUG-013 — implementation plan

[← Finding](../../findings/BUG-013-failed-companion-deliveries-are-recorded-as-successfully-delivered.md) · [← Audit index](../../README.md)

> This is a planning document, not a ready-to-apply patch. Revalidate line numbers and surrounding code against the branch being changed.

| Field | Value |
|---|---|
| Finding | **Failed companion deliveries are recorded as successfully delivered** |
| Classification | **Confirmed defect** |
| Severity | **High** |
| Confidence | **Confirmed** |
| Area | Companion routing / deduplication |
| Components | OpenHop Repeater |
| Audit date | 2026-07-17 |

## Objective

Fix the confirmed defect: Delivery state should be committed only after at least one bridge confirms authenticated handling. Failures should remain eligible for the next duplicate copy.

## Current behavior to preserve in the reproduction

`_fan_out_to_bridges()` returns whether any bridge authenticated the packet. Its caller ignores that distinction and unconditionally calls `_mark_delivered_to_companions()`. This directly contradicts the helper documentation, which says failed delivery must remain retryable.

## Required outcome

Return and propagate a structured delivery result. Mark the logical packet delivered only when `authenticated_count > 0`; retain policy-drop decisions separately so intentional suppression is not retried.

## Repositories and files to inspect or change

| Repository | Path | Purpose |
|---|---|---|
| OpenHop Repeater | `repeater/packet_router.py` | Evidence lines 173–205 |

The listed paths are the minimum evidence/change surface identified by the audit. Before editing, search the repositories for the affected symbols, field names and response keys to find indirect consumers, tests and generated artifacts.

## Implementation work packages

1. Introduce a structured companion delivery result containing attempted, authenticated/delivered, failed and policy-skipped counts.
2. Commit deduplication/delivered state only when at least one candidate authenticated and accepted the logical packet. Keep intentional policy suppression separate from transport/authentication failure.
3. Ensure exceptions and negative acknowledgements propagate as failed delivery rather than truthy completion.
4. Add logging/metrics that distinguish no candidate, authentication failure, bridge exception, policy drop and successful delivery.

## Decisions and assumptions to double-check

- [ ] Define whether policy drops count as terminally handled.
- [ ] Check retry/deduplication interaction to avoid duplicate user-visible delivery.
- [ ] Ensure aggregate results do not expose identity secrets.

## Test plan

### Existing test modules likely to extend

- OpenHop Repeater: `tests/test_packet_router.py`, `tests/test_identity_collision_preflight.py`

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

- Roll out with delivery/queue metrics enabled and watch retry, duplicate and queue-depth behavior before removing old safeguards.

- Keep the previous behavior behind a temporary compatibility alias/adapter only when an external contract requires it.
- Make rollback possible without hand-editing corrupted state. Configuration/data migrations need an explicit reverse or safe fallback path.
- Update documentation, OpenAPI/UI text and examples in the same change when user-visible semantics or field names change.

## Definition of done

- [ ] The behavior described in `BUG-013-failed-companion-deliveries-are-recorded-as-successfully-delivered.md` can no longer be reproduced.
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
