# BUG-045 — implementation plan

[← Finding](../../findings/BUG-045-mesh-cli-security-commands-write-the-wrong-config-section.md) · [← Audit index](../../README.md)

> This is a planning document, not a ready-to-apply patch. Revalidate line numbers and surrounding code against the branch being changed.
> Verification status: **three independent checks passed against the supplied snapshots**.

| Field | Value |
|---|---|
| Finding | **Mesh CLI security commands write a configuration section authentication does not read** |
| Classification | **Confirmed defect** |
| Severity | **High** |
| Confidence | **Triple-verified** |
| Area | Authentication configuration |
| Components | OpenHop Repeater |
| Audit date | 2026-07-17 |

## Objective

Eliminate the confirmed contract violation without changing adjacent behavior that is not required by this finding.

## Current behavior

Mesh CLI writes top-level `security.password` and `security.guest_password`. `LoginHelper` reads `repeater.security.admin_password` and `guest_password`, matching the example configuration. Commands can claim credentials changed while actual authentication continues using the old nested values.

## Required outcome

Every credential writer and reader must use one canonical schema and field names.

## Repositories and files to inspect or change

| Repository | Path | Purpose |
|---|---|---|
| OpenHop Repeater | `repeater/handler_helpers/mesh_cli.py` | Confirmed evidence and primary change surface |
| OpenHop Repeater | `repeater/handler_helpers/login.py` | Confirmed evidence and primary change surface |
| OpenHop Repeater | `config.yaml.example` | Confirmed evidence and primary change surface |

Before editing, search both repositories for every affected symbol, configuration key, response field and test double. Generated assets and external firmware interfaces must be updated only when they are actual consumers of the corrected contract.

## Implementation work packages

1. Move Mesh CLI writers/getters to `repeater.security.admin_password` and `guest_password`.
2. Provide an explicit migration for any already-written top-level legacy values; do not silently prioritize ambiguous duplicates.
3. Centralize credential access through a typed security configuration helper.

## Decisions and assumptions to double-check

- [ ] Search deployment docs for legacy top-level `security` use before migration.
- [ ] Ensure redaction/logging never exposes credentials during migration or command responses.

## Test plan

### Existing test modules likely to extend

- OpenHop Repeater: `tests/test_handler_helpers_mesh_cli.py`
- OpenHop Repeater: `tests/test_handler_helpers_trace_discovery_login.py`

### Required focused tests

- [ ] Preserve verification method 1: static writer/reader mismatch — CLI and LoginHelper use different subtrees and admin key names.
- [ ] Preserve verification method 2: command state separation — Commands report success while the authentication subtree remains unchanged.
- [ ] Preserve verification method 3: actual loginhelper — The ACL is built with the old nested credentials.
- [ ] Add at least one negative test proving unrelated traffic/state is not changed by the correction.
- [ ] Add failure, timeout, cancellation or restart coverage where the affected path owns resources or persistence.
- [ ] Ensure the regression test fails for the documented reason on the supplied snapshot and passes after the implementation.

### Integration verification

- [ ] Exercise the real public entry point, not only the isolated helper.
- [ ] Verify effective runtime state, persisted state and user-visible status agree.
- [ ] Run the complete Core and Repeater suites plus all five triple-verification scripts.
- [ ] Re-test with the relevant real hardware/firmware where the finding concerns a physical adapter; the audit uses deterministic fakes for reproducibility.

## Compatibility, rollout and rollback

- Preserve old field names or return shapes only through explicit temporary compatibility adapters; do not keep two competing sources of truth.
- Add diagnostics for rejected, queued, applied and confirmed states where those are currently conflated.
- Roll out hardware/protocol changes on one test node first and retain a configuration rollback path.
- Update API/OpenAPI/UI/help text in the same change whenever the user-facing contract changes.

## Definition of done

- [ ] All three original verification methods no longer reproduce the defect.
- [ ] No new global state, stale callback, partial persistence or false-success path is introduced.
- [ ] The affected public API/CLI/lifecycle call reports the actual outcome.
- [ ] Complete project suites and focused regression tests pass.
- [ ] Documentation and implementation use one canonical contract.

## Suggested implementation order

1. Add the three focused regression cases.
2. Define the canonical contract/state model.
3. Implement the smallest correction at the owning layer.
4. Migrate direct callers and test doubles.
5. Add failure/restart/concurrency coverage.
6. Run full verification and hardware integration where applicable.
