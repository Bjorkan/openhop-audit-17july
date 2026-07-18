# BUG-043 — implementation plan

[← Finding](../../findings/BUG-043-sx1262-sync-word-is-never-programmed.md) · [← Audit index](../../README.md)

> This is a planning document, not a ready-to-apply patch. Revalidate line numbers and surrounding code against the branch being changed.
> Verification status: **three independent checks passed against the supplied snapshots**.

| Field | Value |
|---|---|
| Finding | **Configured SX1262 sync word is never programmed** |
| Classification | **Confirmed defect** |
| Severity | **High** |
| Confidence | **Triple-verified** |
| Area | SX1262 hardware configuration |
| Components | OpenHop Core + OpenHop Repeater |
| Audit date | 2026-07-17 |

## Objective

Eliminate the confirmed contract violation without changing adjacent behavior that is not required by this finding.

## Current behavior

Repeater parses and passes `sync_word`; `SX1262Radio` stores it, but initialization never calls `setSyncWord`. The bundled low-level `SX126x.setSyncWord()` itself contains no active register write. The radio therefore uses hardware/default state rather than the configured network sync word.

## Required outcome

Initialization and live/reconnect configuration must write the configured sync word to the correct SX126x registers and verify the operation where possible.

## Repositories and files to inspect or change

| Repository | Path | Purpose |
|---|---|---|
| OpenHop Repeater | `repeater/config.py` | Confirmed evidence and primary change surface |
| OpenHop Core | `src/openhop_core/hardware/sx1262_wrapper.py` | Confirmed evidence and primary change surface |
| OpenHop Core | `src/openhop_core/hardware/lora/LoRaRF/SX126x.py` | Confirmed evidence and primary change surface |

Before editing, search both repositories for every affected symbol, configuration key, response field and test double. Generated assets and external firmware interfaces must be updated only when they are actual consumers of the corrected contract.

## Implementation work packages

1. Implement the correct SX126x sync-word register write in the low-level driver.
2. Call it from `SX1262Radio.begin()` in the correct order before RX starts.
3. Add validation/range normalization and reconnect tests.

## Decisions and assumptions to double-check

- [ ] Verify whether configuration values use the one-byte MeshCore form or the SX126x two-byte register form.
- [ ] Confirm private/public network mappings and byte order against hardware documentation/firmware behavior.

## Test plan

### Existing test modules likely to extend

- OpenHop Core: `tests/test_sx1262_wrapper.py`
- OpenHop Core: `tests/test_sx1262_wrapper_concurrency.py`
- OpenHop Repeater: `tests/test_config_radio.py`

### Required focused tests

- [ ] Preserve verification method 1: static config-to-driver trace — The value is parsed and stored, but no wrapper path calls the low-level setter.
- [ ] Preserve verification method 2: low-level call — Calling `setSyncWord(0x3444)` performs zero register writes.
- [ ] Preserve verification method 3: full initialization — Fake-hardware initialization records no sync-word operation.
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
