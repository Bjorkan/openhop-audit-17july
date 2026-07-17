# BUG-009 — implementation plan

[← Finding](../../findings/BUG-009-configuration-import-reports-success-even-when-persistence-fails.md) · [← Audit index](../../README.md)

> This is a planning document, not a ready-to-apply patch. Revalidate line numbers and surrounding code against the branch being changed.
> Reverification status: **confirmed against the supplied snapshot**.

| Field | Value |
|---|---|
| Finding | **Configuration import reports success even when persistence fails** |
| Classification | **Confirmed defect** |
| Severity | **High** |
| Confidence | **Confirmed** |
| Area | Backup and restore |
| Components | OpenHop Repeater + Web UI |
| Audit date | 2026-07-17 |

## Objective

Fix the confirmed defect: Import should perform one validated transaction and return success only when persistence succeeds. Live-update failures should be distinguished from disk failures.

## Current behavior to preserve in the reproduction

The UI can tell the operator that a restore completed while the process only holds transient in-memory changes. A restart then loses the imported configuration.

## Required outcome

Capture the `update_and_save` result, remove the duplicate save, rollback in-memory changes on failure, and expose `live_updated`/`restart_required` accurately.

## Repositories and files to inspect or change

| Repository | Path | Purpose |
|---|---|---|
| OpenHop Repeater | `repeater/web/api_endpoints.py` | Evidence lines 7392–7413 |
| OpenHop Repeater | `repeater/config_manager.py` | Evidence lines 359–417 |
| OpenHop Repeater Web UI | `Frontend source corresponding to repeater/web/html/assets/ (not supplied)` | Locate before implementation; generated bundle must not be edited as source |

The listed paths are the minimum evidence/change surface identified by the audit. Before editing, search the repositories for the affected symbols, field names and response keys to find indirect consumers, tests and generated artifacts.

## Implementation work packages

1. Build the imported configuration as an isolated candidate and validate it completely before changing shared runtime state.
2. Call a single transactional save/apply operation; remove the second independent `save_to_file()` call.
3. If persistence fails, retain the previous in-memory and on-disk configuration. If live apply fails after persistence, return an explicit restart-required or rollback result according to policy.
4. Ensure the API status and message are derived from the commit result and cannot report success with `saved: false`.

## Decisions and assumptions to double-check

- [ ] Check `update_and_save()` already mutates runtime before returning.
- [ ] Verify backup/restore of previous file on failure.
- [ ] Ensure failed imports do not emit success audit logs.

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

- The supplied snapshot contains compiled frontend assets but no `.vue`, `.ts` or `.tsx` source. Apply UI work in the actual source repository, rebuild, then replace generated assets.

- Keep the previous behavior behind a temporary compatibility alias/adapter only when an external contract requires it.
- Make rollback possible without hand-editing corrupted state. Configuration/data migrations need an explicit reverse or safe fallback path.
- Update documentation, OpenAPI/UI text and examples in the same change when user-visible semantics or field names change.

## Definition of done

- [ ] The behavior described in `BUG-009-configuration-import-reports-success-even-when-persistence-fails.md` can no longer be reproduced.
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
