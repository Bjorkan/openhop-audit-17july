# BUG-014 — implementation plan

[← Finding](../../findings/BUG-014-a-failing-companion-bridge-can-shadow-another-local-identity-with-the-same-destination-hash.md) · [← Audit index](../../README.md)

> This is a planning document, not a ready-to-apply patch. Revalidate line numbers and surrounding code against the branch being changed.
> Reverification status: **confirmed against the supplied snapshot**.

| Field | Value |
|---|---|
| Finding | **A failing companion bridge can shadow another local identity with the same destination hash** |
| Classification | **Confirmed defect** |
| Severity | **High** |
| Confidence | **Confirmed** |
| Area | Local identity routing / collision handling |
| Components | OpenHop Repeater |
| Audit date | 2026-07-17 |

## Objective

Fix the confirmed defect: Each local candidate should be isolated. One broken candidate must not prevent another candidate with the same one-byte hash from attempting decryption.

## Current behavior to preserve in the reproduction

`_consume_via_local_candidates()` directly awaits the companion bridge without the exception isolation used by `_fan_out_to_bridges()`. If that bridge raises, the helper candidate is skipped and the route task fails, even though it may be the identity that can authenticate the packet.

## Required outcome

Use one shared candidate-delivery helper that catches/logs per-candidate failures and continues. Return true if any candidate authenticates.

## Repositories and files to inspect or change

| Repository | Path | Purpose |
|---|---|---|
| OpenHop Repeater | `repeater/packet_router.py` | Evidence lines 276–328 |

The listed paths are the minimum evidence/change surface identified by the audit. Before editing, search the repositories for the affected symbols, field names and response keys to find indirect consumers, tests and generated artifacts.

## Implementation work packages

1. Resolve all local identity candidates for a destination hash and attempt them independently.
2. Catch and record failures per candidate, then continue to remaining candidates. A single broken bridge must not terminate collision resolution.
3. Return success if any candidate authenticates; return an aggregate failure only after every candidate has been evaluated.
4. Preserve deterministic ordering and rate limits so collision handling cannot be abused for unbounded work.

## Decisions and assumptions to double-check

- [ ] Check collision candidate count is bounded.
- [ ] Confirm candidate order cannot starve valid identities.
- [ ] Verify a candidate exception does not corrupt shared bridge state.

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

- [ ] The behavior described in `BUG-014-a-failing-companion-bridge-can-shadow-another-local-identity-with-the-same-destination-hash.md` can no longer be reproduced.
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
