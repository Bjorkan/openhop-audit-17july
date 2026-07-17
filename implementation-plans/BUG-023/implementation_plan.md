# BUG-023 — implementation plan

[← Finding](../../findings/BUG-023-a-failed-admin-password-save-still-changes-the-running-password.md) · [← Audit index](../../README.md)

> This is a planning document, not a ready-to-apply patch. Revalidate line numbers and surrounding code against the branch being changed.

| Field | Value |
|---|---|
| Finding | **A failed admin-password save still changes the running password** |
| Classification | **Confirmed defect** |
| Severity | **High** |
| Confidence | **Confirmed** |
| Area | Authentication / configuration transactions |
| Components | OpenHop Repeater Web API |
| Audit date | 2026-07-17 |

## Objective

Fix the confirmed defect: A failed password-change transaction must leave the active and persisted credential unchanged.

## Current behavior to preserve in the reproduction

After a disk failure, the old credential no longer matches runtime login checks even though the change response says failure. Restart restores the old persisted password, creating a second reversal. This can lock out an operator or make incident recovery unpredictable.

## Required outcome

Validate and stage the new password, persist a copied configuration atomically, then swap the runtime reference. At minimum restore the previous value in every failure path.

## Repositories and files to inspect or change

| Repository | Path | Purpose |
|---|---|---|
| OpenHop Repeater | `repeater/web/auth_endpoints.py` | Evidence lines 537–605 |

The listed paths are the minimum evidence/change surface identified by the audit. Before editing, search the repositories for the affected symbols, field names and response keys to find indirect consumers, tests and generated artifacts.

## Implementation work packages

1. Validate password policy and construct a candidate configuration without changing the active authentication reference.
2. Persist the candidate atomically. Only after success should the running auth component swap to the new credential/hash.
3. On any error, preserve the old password in memory and on disk and avoid partially invalidating sessions unless explicitly intended.
4. Review secret handling so plaintext values are not logged, returned or retained longer than needed.

## Decisions and assumptions to double-check

- [ ] Confirm hashing/storage format and migration behavior.
- [ ] Check active sessions and CSRF tokens.
- [ ] Avoid logging plaintext or secret-bearing exceptions.

## Test plan

### Existing test modules likely to extend

- OpenHop Repeater: `tests/test_config_manager.py`
- OpenHop Repeater: `tests/test_api_endpoints_core_coverage.py` and the domain-specific endpoint test module
- OpenHop Repeater: `tests/test_auth_endpoints.py`, `tests/test_auth_components.py`

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

- [ ] The behavior described in `BUG-023-a-failed-admin-password-save-still-changes-the-running-password.md` can no longer be reproduced.
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
