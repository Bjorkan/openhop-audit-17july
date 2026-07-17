# BUG-006 — implementation plan

[← Finding](../../findings/BUG-006-adaptive-advert-thresholds-saved-by-the-ui-are-ignored.md) · [← Audit index](../../README.md)

> This is a planning document, not a ready-to-apply patch. Revalidate line numbers and surrounding code against the branch being changed.
> Reverification status: **confirmed against the supplied snapshot**.

| Field | Value |
|---|---|
| Finding | **Adaptive advert thresholds saved by the UI are ignored** |
| Classification | **Confirmed defect** |
| Severity | **Medium** |
| Confidence | **Confirmed** |
| Area | Advert rate limiting |
| Components | OpenHop Repeater + Web UI |
| Audit date | 2026-07-17 |

## Objective

Fix the confirmed defect: One canonical schema and one parser must define both names and boundary semantics.

## Current behavior to preserve in the reproduction

With the shipped keys, runtime silently falls back to 1.0, 5.0 and 15.0. The UI can display the saved values while decisions are made with different thresholds.

## Required outcome

Map `quiet_max → normal boundary`, `normal_max → busy boundary`, and `busy_max → congested boundary`; migrate legacy names explicitly and validate ascending order.

## Repositories and files to inspect or change

| Repository | Path | Purpose |
|---|---|---|
| OpenHop Repeater | `config.yaml.example` | Evidence lines 100–114 |
| OpenHop Repeater | `repeater/web/api_endpoints.py` | Evidence lines 1989–2011 |
| OpenHop Repeater | `repeater/handler_helpers/advert.py` | Evidence lines 63–87 |
| OpenHop Repeater Web UI | `Frontend source corresponding to repeater/web/html/assets/ (not supplied)` | Locate before implementation; generated bundle must not be edited as source |

The listed paths are the minimum evidence/change surface identified by the audit. Before editing, search the repositories for the affected symbols, field names and response keys to find indirect consumers, tests and generated artifacts.

## Implementation work packages

1. Choose and document canonical threshold names (`quiet_max`, `normal_max`, `busy_max`) and their tier-boundary semantics.
2. Update advert-limiter initialization and live reload to parse the same keys through one helper. Support legacy keys only through an explicit migration layer with warnings.
3. Validate finite numeric values and strict ascending order before committing configuration.
4. Update the UI labels/help text so each threshold describes the tier transition it controls.

## Decisions and assumptions to double-check

- [ ] Confirm old configurations in the field use legacy threshold names.
- [ ] Decide behavior for equal/out-of-order thresholds.
- [ ] Check EWMA units match threshold labels.

## Test plan

### Existing test modules likely to extend

- OpenHop Repeater: `tests/test_handler_helpers_acl_advert.py`
- OpenHop Repeater: `tests/test_api_endpoints_core_coverage.py` and the domain-specific endpoint test module

### Required test cases

- [ ] Add a focused regression test that reproduces the current defect before the implementation and fails for the documented reason.
- [ ] Add a success-path test proving the effective runtime state, persisted state and API/UI-visible state agree after the change where those layers are involved.
- [ ] Use a fake clock and boundary cases immediately before, at and after the configured window/limit.
- [ ] Add contract tests with representative serialized responses/requests and a frontend test for the displayed state.
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

- [ ] The behavior described in `BUG-006-adaptive-advert-thresholds-saved-by-the-ui-are-ignored.md` can no longer be reproduced.
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
