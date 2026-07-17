# BUG-002 — implementation plan

[← Finding](../../findings/BUG-002-configuration-screens-misread-the-standard-api-response-envelope.md) · [← Audit index](../../README.md)

> This is a planning document, not a ready-to-apply patch. Revalidate line numbers and surrounding code against the branch being changed.

| Field | Value |
|---|---|
| Finding | **Configuration screens misread the standard API response envelope** |
| Classification | **Confirmed defect** |
| Severity | **Medium** |
| Confidence | **Confirmed** |
| Area | Web UI / API contract |
| Components | OpenHop Repeater Web UI |
| Audit date | 2026-07-17 |

## Objective

Fix the confirmed defect: Every caller should normalize the response once and then evaluate the same envelope. A shared helper should return `{ok, payload, error}`.

## Current behavior to preserve in the reproduction

`APIEndpoints._success()` returns `{success: true, data: payload}` and Axios returns that body as `response.data`. Some forms inspect `response.data.message` instead of `response.data.data.message`; the advert form checks `response.success` instead of `response.data.success`; the terminal similarly checks the Axios response object.

## Required outcome

Fix the affected radio, repeater, duty-cycle, advert-rate-limit and terminal handlers, then centralize envelope parsing to prevent recurrence.

## Repositories and files to inspect or change

| Repository | Path | Purpose |
|---|---|---|
| OpenHop Repeater | `repeater/web/api_endpoints.py` | Evidence lines 268–275 |
| OpenHop Repeater Web UI | `Frontend source corresponding to repeater/web/html/assets/ (not supplied)` | Locate before implementation; generated bundle must not be edited as source |

The listed paths are the minimum evidence/change surface identified by the audit. Before editing, search the repositories for the affected symbols, field names and response keys to find indirect consumers, tests and generated artifacts.

## Implementation work packages

1. Locate the unminified frontend source for radio, repeater, duty-cycle, advert-rate-limit and terminal mutations. Do not patch generated files under `repeater/web/html/assets/` directly.
2. Introduce a single response normalizer that unwraps Axios and the backend `{success, data, error}` envelope into a stable `{ok, payload, error}` result.
3. Replace every ad-hoc check of `response.success`, `response.data.message` and `response.data.data` with the helper. Preserve endpoint-specific payload fields but centralize success/error determination.
4. Rebuild the frontend bundle reproducibly and verify generated assets contain no old response-access patterns.

## Decisions and assumptions to double-check

- [ ] Identify the real frontend source repository/build commit corresponding to the bundled assets.
- [ ] Confirm whether any endpoints intentionally return a legacy unwrapped response.
- [ ] Check transport errors and HTTP non-2xx responses are normalized separately from backend validation errors.

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

- [ ] The behavior described in `BUG-002-configuration-screens-misread-the-standard-api-response-envelope.md` can no longer be reproduced.
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
