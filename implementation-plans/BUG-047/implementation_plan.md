# BUG-047 — implementation plan

[← Finding](../../findings/BUG-047-local-advert-interval-is-saved-and-displayed-but-never-scheduled.md) · [← Audit index](../../README.md)

> This is a planning document, not a ready-to-apply patch. Revalidate line numbers and surrounding code against the branch being changed.
> Verification status: **three independent checks passed against the supplied snapshots**.

| Field | Value |
|---|---|
| Finding | **Local advert interval is saved and displayed but never used by the scheduler** |
| Classification | **Confirmed defect** |
| Severity | **Medium** |
| Confidence | **Triple-verified** |
| Area | Advert scheduling / API consistency |
| Components | OpenHop Repeater + Web UI |
| Audit date | 2026-07-17 |

## Objective

Eliminate the confirmed contract violation without changing adjacent behavior that is not required by this finding.

## Current behavior

The API accepts and persists `advert_interval_minutes`, and stats expose it. The only periodic advert timer reads `send_advert_interval_hours`. Changing the local interval therefore appears successful and visible but has no runtime scheduling effect.

## Required outcome

A user-visible advert interval must control a clearly identified advert scheduler, or the unused setting must be removed from API/UI.

## Repositories and files to inspect or change

| Repository | Path | Purpose |
|---|---|---|
| OpenHop Repeater | `repeater/web/api_endpoints.py` | Confirmed evidence and primary change surface |
| OpenHop Repeater | `repeater/engine.py` | Confirmed evidence and primary change surface |

Before editing, search both repositories for every affected symbol, configuration key, response field and test double. Generated assets and external firmware interfaces must be updated only when they are actual consumers of the corrected contract.

## Implementation work packages

1. Clarify local versus flood advert semantics and connect each setting to its intended scheduler.
2. Use one canonical field/unit per advert type across startup, reload, API, CLI, telemetry and documentation.
3. Return effective next-run information so the UI can verify the change.

## Decisions and assumptions to double-check

- [ ] Confirm whether “local advert” should be a separate transmission path that is currently missing.
- [ ] Avoid unintentionally increasing airtime by enabling two periodic advert loops.

## Test plan

### Existing test modules likely to extend

- OpenHop Repeater: `tests/test_api_endpoints_core_coverage.py`
- OpenHop Repeater: `tests/test_handler_helpers_acl_advert.py`
- OpenHop Repeater: `tests/test_path_hash_mode_advert.py`

### Required focused tests

- [ ] Preserve verification method 1: static writer/telemetry/scheduler trace — The accepted field is never consumed by the timer.
- [ ] Preserve verification method 2: runtime reload — Reload retains the unrelated ten-hour scheduler value despite a one-minute local interval.
- [ ] Preserve verification method 3: actual timer decision — Two minutes after the last advert, the real loop sends nothing for a one-minute setting.
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
