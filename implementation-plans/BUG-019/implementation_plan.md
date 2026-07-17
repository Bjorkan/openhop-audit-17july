# BUG-019 — implementation plan

[← Finding](../../findings/BUG-019-the-openapi-duty-cycle-request-schema-does-not-match-the-implemented-endpoint.md) · [← Audit index](../../README.md)

> This is a planning document, not a ready-to-apply patch. Revalidate line numbers and surrounding code against the branch being changed.

| Field | Value |
|---|---|
| Finding | **The OpenAPI duty-cycle request schema does not match the implemented endpoint** |
| Classification | **Confirmed defect** |
| Severity | **Medium** |
| Confidence | **Confirmed** |
| Area | Public API contract |
| Components | OpenHop Repeater |
| Audit date | 2026-07-17 |

## Objective

Fix the confirmed defect: The machine-readable API contract must describe the request actually accepted by the deployed endpoint.

## Current behavior to preserve in the reproduction

A generated or documentation-following client sends a schema-valid request that the server rejects as “No valid settings provided.” The actual percentage-based semantics and accepted range are absent from the published contract.

## Required outcome

Replace the stale fields and add validation constraints/examples. Add a contract test that derives a representative request from the OpenAPI schema and submits it to the endpoint.

## Repositories and files to inspect or change

| Repository | Path | Purpose |
|---|---|---|
| OpenHop Repeater | `repeater/web/openapi.yaml` | Evidence lines 761–794 |
| OpenHop Repeater | `repeater/web/api_endpoints.py` | Evidence lines 1925–1978 |

The listed paths are the minimum evidence/change surface identified by the audit. Before editing, search the repositories for the affected symbols, field names and response keys to find indirect consumers, tests and generated artifacts.

## Implementation work packages

1. Update the duty-cycle request model in `openapi.yaml` to the exact field names, types, constraints and nullable/optional behavior accepted by the endpoint.
2. Align examples and response schema with the standard API envelope and effective/restart-required fields.
3. Add a contract test that generates representative valid and invalid payloads from the schema and submits them to the real endpoint handler.
4. Search the remainder of OpenAPI for similar stale endpoint schemas while touching the generator/test infrastructure.

## Decisions and assumptions to double-check

- [ ] Confirm the deployed API version and compatibility promises.
- [ ] Check generated documentation and clients.
- [ ] Validate numeric units are percent rather than milliseconds.

## Test plan

### Existing test modules likely to extend

- OpenHop Repeater: `tests/test_api_endpoints_core_coverage.py` and the domain-specific endpoint test module
- OpenHop Repeater: `tests/test_openapi_identity_contract.py` or a new generalized OpenAPI contract module

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

- Treat field renames/envelope changes as a compatibility migration. Keep aliases or version the API where external clients may depend on the old contract.

- Keep the previous behavior behind a temporary compatibility alias/adapter only when an external contract requires it.
- Make rollback possible without hand-editing corrupted state. Configuration/data migrations need an explicit reverse or safe fallback path.
- Update documentation, OpenAPI/UI text and examples in the same change when user-visible semantics or field names change.

## Definition of done

- [ ] The behavior described in `BUG-019-the-openapi-duty-cycle-request-schema-does-not-match-the-implemented-endpoint.md` can no longer be reproduced.
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
