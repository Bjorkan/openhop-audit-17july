# BUG-012 — implementation plan

[← Finding](../../findings/BUG-012-quick-mode-and-duty-controls-are-volatile-while-the-terminal-labels-them-persisted.md) · [← Audit index](../../README.md)

> This is a planning document, not a ready-to-apply patch. Revalidate line numbers and surrounding code against the branch being changed.
> Reverification status: **confirmed against the supplied snapshot**.

| Field | Value |
|---|---|
| Finding | **Quick mode and duty controls are volatile while the terminal labels them persisted** |
| Classification | **Confirmed defect** |
| Severity | **Medium** |
| Confidence | **Confirmed** |
| Area | Runtime controls / persistence / UI |
| Components | OpenHop Repeater + Web UI |
| Audit date | 2026-07-17 |

## Objective

Fix the confirmed defect: The control must be explicitly persistent or explicitly session-only. UI text and API fields must match that choice.

## Current behavior to preserve in the reproduction

The endpoints never call `ConfigManager`. Because they mutate the same shared config object, a later unrelated save can also persist the change accidentally, making persistence timing nondeterministic.

## Required outcome

Prefer routing both endpoints through the transactional config helper and returning the standard envelope. If volatility is intentional, rename them and display “until restart” without fabricating persistence.

## Repositories and files to inspect or change

| Repository | Path | Purpose |
|---|---|---|
| OpenHop Repeater | `repeater/web/api_endpoints.py` | Evidence lines 1868–1915 |
| OpenHop Repeater Web UI | `Frontend source corresponding to repeater/web/html/assets/ (not supplied)` | Locate before implementation; generated bundle must not be edited as source |

The listed paths are the minimum evidence/change surface identified by the audit. Before editing, search the repositories for the affected symbols, field names and response keys to find indirect consumers, tests and generated artifacts.

## Implementation work packages

1. Make an explicit product decision per control: persistent configuration or runtime-only override. The API, terminal wording and UI must expose the same contract.
2. For persistent controls, route changes through transactional configuration save and live apply. For runtime-only controls, use names such as “temporary”/“until restart” and never report saved state.
3. Return the effective current mode and persistence status in the response.
4. Verify startup behavior restores persistent values and clears intentionally volatile overrides.

## Decisions and assumptions to double-check

- [ ] Confirm user expectations and backward compatibility for existing API clients.
- [ ] Check terminal command output and web UI labels together.
- [ ] Verify temporary overrides interact predictably with later persistent updates.

## Test plan

### Existing test modules likely to extend

- OpenHop Repeater: `tests/test_api_endpoints_core_coverage.py` and the domain-specific endpoint test module

### Required test cases

- [ ] Add a focused regression test that reproduces the current defect before the implementation and fails for the documented reason.
- [ ] Add a success-path test proving the effective runtime state, persisted state and API/UI-visible state agree after the change where those layers are involved.
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
- Treat field renames/envelope changes as a compatibility migration. Keep aliases or version the API where external clients may depend on the old contract.

- Keep the previous behavior behind a temporary compatibility alias/adapter only when an external contract requires it.
- Make rollback possible without hand-editing corrupted state. Configuration/data migrations need an explicit reverse or safe fallback path.
- Update documentation, OpenAPI/UI text and examples in the same change when user-visible semantics or field names change.

## Definition of done

- [ ] The behavior described in `BUG-012-quick-mode-and-duty-controls-are-volatile-while-the-terminal-labels-them-persisted.md` can no longer be reproduced.
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
