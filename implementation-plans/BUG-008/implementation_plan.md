# BUG-008 — implementation plan

[← Finding](../../findings/BUG-008-configuration-export-cannot-be-fully-restored-by-configuration-import.md) · [← Audit index](../../README.md)

> This is a planning document, not a ready-to-apply patch. Revalidate line numbers and surrounding code against the branch being changed.
> Reverification status: **confirmed against the supplied snapshot**.

| Field | Value |
|---|---|
| Finding | **Configuration export cannot be fully restored by configuration import** |
| Classification | **Confirmed defect** |
| Severity | **High** |
| Confidence | **Confirmed** |
| Area | Backup and restore |
| Components | OpenHop Repeater + Web UI |
| Audit date | 2026-07-17 |

## Objective

Fix the confirmed defect: Every supported exported section must have an explicit restore policy. Unsupported sections should be listed as errors, not silently skipped.

## Current behavior to preserve in the reproduction

The import allowlist omits at least `duty_cycle`, `gps`, `http`, `policy`, `sensors`, and `storage`. A backup can therefore report successful import while leaving these settings unchanged; importing a backup containing only one omitted section fails as “no valid sections.”

## Required outcome

Derive importability from a shared schema, return `sections_skipped` with reasons, and add an export→import round-trip test covering every top-level section.

## Repositories and files to inspect or change

| Repository | Path | Purpose |
|---|---|---|
| OpenHop Repeater | `repeater/web/api_endpoints.py` | Evidence lines 7166–7240 |
| OpenHop Repeater Web UI | `Frontend source corresponding to repeater/web/html/assets/ (not supplied)` | Locate before implementation; generated bundle must not be edited as source |

The listed paths are the minimum evidence/change surface identified by the audit. Before editing, search the repositories for the affected symbols, field names and response keys to find indirect consumers, tests and generated artifacts.

## Implementation work packages

1. Create one enumerable schema of importable top-level sections and use it for both export and import.
2. Decide which sections are portable, host-specific, secret-bearing or runtime-only. Redact or separately gate secrets rather than silently omitting arbitrary sections.
3. Make import report applied, skipped and rejected sections with reasons. Unknown future sections must not disappear behind a generic success.
4. Add a full export→fresh-config→import round trip and compare all supported values semantically.

## Decisions and assumptions to double-check

- [ ] Classify secrets and machine-specific paths before round-trip restoration.
- [ ] Define compatibility behavior across schema versions.
- [ ] Ensure imports cannot write arbitrary files or unsafe object types.

## Test plan

### Existing test modules likely to extend

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
- Treat field renames/envelope changes as a compatibility migration. Keep aliases or version the API where external clients may depend on the old contract.

- Keep the previous behavior behind a temporary compatibility alias/adapter only when an external contract requires it.
- Make rollback possible without hand-editing corrupted state. Configuration/data migrations need an explicit reverse or safe fallback path.
- Update documentation, OpenAPI/UI text and examples in the same change when user-visible semantics or field names change.

## Definition of done

- [ ] The behavior described in `BUG-008-configuration-export-cannot-be-fully-restored-by-configuration-import.md` can no longer be reproduced.
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
