# BUG-010 — implementation plan

[← Finding](../../findings/BUG-010-rejected-multi-field-configuration-requests-leave-partial-in-memory-changes.md) · [← Audit index](../../README.md)

> This is a planning document, not a ready-to-apply patch. Revalidate line numbers and surrounding code against the branch being changed.
> Reverification status: **confirmed against the supplied snapshot**.

| Field | Value |
|---|---|
| Finding | **Rejected multi-field configuration requests leave partial in-memory changes** |
| Classification | **Confirmed defect** |
| Severity | **Medium** |
| Confidence | **Confirmed** |
| Area | Configuration transactions |
| Components | OpenHop Repeater |
| Audit date | 2026-07-17 |

## Objective

Fix the confirmed defect: A failed request must leave both runtime and persisted configuration unchanged.

## Current behavior to preserve in the reproduction

For example, `update_radio_config` writes TX power before validating bandwidth. A request containing valid power and invalid bandwidth is rejected, yet the shared config retains the new power. An unrelated later save can persist that hidden partial change.

## Required outcome

Validate into a deep copy or typed request model, then commit the full change only after all validation passes. Roll back if save or live apply fails.

## Repositories and files to inspect or change

| Repository | Path | Purpose |
|---|---|---|
| OpenHop Repeater | `repeater/web/api_endpoints.py` | Evidence lines 3962–4020 |
| OpenHop Repeater | `repeater/config_manager.py` | Evidence lines 359–417 |

The listed paths are the minimum evidence/change surface identified by the audit. Before editing, search the repositories for the affected symbols, field names and response keys to find indirect consumers, tests and generated artifacts.

## Implementation work packages

1. Parse every supplied field into a typed request or deep-copied candidate configuration before mutating the active dictionary.
2. Run cross-field validation after individual parsing so invalid later fields cannot leave earlier fields applied.
3. Commit persistence and live application through one transaction boundary, with a snapshot available for rollback.
4. Audit all multi-field endpoints for direct writes during validation and migrate them to the same pattern.

## Decisions and assumptions to double-check

- [ ] Find every endpoint that writes `self.config` while still validating.
- [ ] Check nested mutable objects are deep-copied.
- [ ] Define how concurrent configuration requests are serialized.

## Test plan

### Existing test modules likely to extend

- OpenHop Repeater: `tests/test_config_manager.py`
- OpenHop Repeater: `tests/test_api_endpoints_core_coverage.py` and the domain-specific endpoint test module

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

- [ ] The behavior described in `BUG-010-rejected-multi-field-configuration-requests-leave-partial-in-memory-changes.md` can no longer be reproduced.
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
