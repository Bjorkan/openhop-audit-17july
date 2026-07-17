# OpenHop Internal Logic and Consistency Audit — 17 July 2026 — Reverified Edition

This edition treats every conclusion in the earlier 17 July audit as untrusted. Both source ZIPs were extracted again, every report was traced through reachable runtime paths and documented contracts, the complete project test suites were rerun, and independent checks were written rather than accepting the earlier reproduction scripts as proof.

The supplied 13 July audit was used only as an organisational/layout reference. Its findings were not imported.

## Audited snapshots

| Project | Snapshot | Notes |
|---|---|---|
| OpenHop Core | Supplied ZIP, package version `1.1.3.dev7` | No `.git` metadata; SHA-256 in `AUDIT-SNAPSHOT.txt` |
| OpenHop Repeater | Supplied dynamic-version source snapshot | No generated `_version.py` or `.git` metadata; SHA-256 in `AUDIT-SNAPSHOT.txt` |
| Previous audit | `openhop-internal-audit-17july-2026-implementation-plans.zip` | Treated as an untrusted claim set |
| Layout reference | `openhop-audit-13july(1).zip` | Structure only |

## Reverification result

| Metric | Result |
|---|---:|
| Original bug claims reviewed | **27** |
| Confirmed active defects | **25** |
| Retracted false positives | **1** (`BUG-002`) |
| Reclassified from bug to possible enhancement | **1** (`BUG-026` → `POSSIBLE-ENHANCEMENT-018`) |
| Original possible enhancements reviewed | **20** |
| Active possible enhancements | **18** |
| Enhancement reports merged | **2** (`019`, `020`) |
| Active implementation plans | **43** |
| Independent reverification checks | **28 passed** |
| Enhancement premise checks | **20 passed** |
| Source-excerpt lines checked | **4,371; 0 mismatches** |
| Core tests | **1,272 passed** |
| Repeater tests | **1,222 passed** |

The earlier audit was materially wrong in two classifications. `BUG-002` is a false positive. The behavior described by former `BUG-026` exists, but the supplied protocol and queue documentation explicitly defines destructive pop and queue-full shedding, so it cannot defensibly remain a bug without a stronger delivery contract.

## Classification rules

A report remains a **bug** only where the supplied code produces a contradictory, lossy, falsely reported or contract-violating result on a reachable path. Documented semantics are not relabeled as bugs merely because a stronger design is preferable. Architectural consolidation or stronger guarantees without a demonstrated contract violation are **possible enhancements**. A helper defect with no supplied call sites is marked latent and low severity.

## Confirmed defects

| Finding | Severity | Area | Components | Summary |
|---|---|---|---|---|
| 🟠 [BUG-001](findings/BUG-001-duty-cycle-budget-usage-is-presented-as-actual-duty-cycle.md) | Medium | Telemetry and dashboard | OpenHop Repeater + Web UI | Duty-cycle budget usage is presented as actual duty cycle |
| 🔴 [BUG-003](findings/BUG-003-live-duty-cycle-limit-changes-do-not-update-the-enforced-limit.md) | High | Duty-cycle enforcement | OpenHop Repeater | Live duty-cycle limit changes do not update the enforced limit |
| 🔴 [BUG-004](findings/BUG-004-live-radio-changes-leave-airtime-estimation-on-the-old-modulation.md) | High | Radio configuration / duty-cycle enforcement | OpenHop Core + OpenHop Repeater | Live radio changes leave airtime estimation on the old modulation |
| 🟠 [BUG-005](findings/BUG-005-sx1262-live-radio-update-omits-transmit-power.md) | Medium | Radio configuration | OpenHop Core + OpenHop Repeater | SX1262 live radio updates omit transmit power |
| 🟠 [BUG-006](findings/BUG-006-adaptive-advert-thresholds-saved-by-the-ui-are-ignored.md) | Medium | Advert rate limiting | OpenHop Repeater + Web UI | Adaptive advert thresholds saved by the UI are ignored |
| 🟠 [BUG-007](findings/BUG-007-advert-rate-limit-update-reports-immediate-success-after-save-failure.md) | Medium | Configuration persistence / UI contract | OpenHop Repeater | Advert-rate-limit update reports immediate success after save or live-update failure |
| 🔴 [BUG-008](findings/BUG-008-configuration-export-cannot-be-fully-restored-by-configuration-import.md) | High | Backup and restore | OpenHop Repeater + Web UI | Configuration export cannot be fully restored by configuration import |
| 🔴 [BUG-009](findings/BUG-009-configuration-import-reports-success-even-when-persistence-fails.md) | High | Backup and restore | OpenHop Repeater + Web UI | Configuration import reports success even when persistence fails |
| 🟠 [BUG-010](findings/BUG-010-rejected-multi-field-configuration-requests-leave-partial-in-memory-changes.md) | Medium | Configuration transactions | OpenHop Repeater | Rejected multi-field configuration requests leave partial in-memory changes |
| 🔴 [BUG-011](findings/BUG-011-gps-clock-corrections-can-reset-rolling-airtime-and-rate-limit-windows.md) | High | Timekeeping / safety limits | OpenHop Repeater | GPS wall-clock corrections can invalidate rolling airtime and rate-limit windows |
| 🟠 [BUG-012](findings/BUG-012-quick-mode-and-duty-controls-are-volatile-while-the-terminal-labels-them-persisted.md) | Medium | Runtime controls / persistence / UI | OpenHop Repeater + Web UI | Quick mode and duty controls are volatile while the terminal labels them persisted |
| 🔴 [BUG-013](findings/BUG-013-failed-companion-deliveries-are-recorded-as-successfully-delivered.md) | High | Companion routing / deduplication | OpenHop Repeater | PATH and protocol-response packets are deduplicated even when no companion authenticates them |
| 🔴 [BUG-014](findings/BUG-014-a-failing-companion-bridge-can-shadow-another-local-identity-with-the-same-destination-hash.md) | High | Local identity routing / collision handling | OpenHop Repeater | A failing companion bridge can shadow another local identity with the same destination hash |
| 🟠 [BUG-015](findings/BUG-015-invalid-packets-are-published-to-mqtt-despite-an-explicit-suppression-request.md) | Medium | Packet publication / external telemetry | OpenHop Repeater | Invalid packets are published to MQTT despite an explicit suppression request |
| 🟠 [BUG-016](findings/BUG-016-the-raw-duplicate-path-bypasses-the-configured-per-packet-duplicate-cap.md) | Medium | Packet history / memory bounds | OpenHop Repeater | The raw duplicate path bypasses the configured per-packet duplicate cap |
| 🟠 [BUG-017](findings/BUG-017-live-reload-can-silently-reduce-the-packet-deduplication-window-from-one-hour-to-one-minute.md) | Medium | Runtime configuration / packet deduplication | OpenHop Repeater | Live reload can use a one-minute deduplication window when `cache_ttl` is absent or below the startup minimum |
| 🟡 [BUG-018](findings/BUG-018-deep-update-nested-replaces-sibling-configuration-instead-of-updating-one-value.md) | Low | Configuration helper semantics | OpenHop Repeater | `update_nested()` replaces sibling configuration instead of updating one deep value |
| 🟠 [BUG-019](findings/BUG-019-the-openapi-duty-cycle-request-schema-does-not-match-the-implemented-endpoint.md) | Medium | Public API contract | OpenHop Repeater | The OpenAPI duty-cycle request schema does not match the implemented endpoint |
| 🔴 [BUG-020](findings/BUG-020-an-update-install-can-overlap-a-version-check-and-be-reported-idle-while-still-running.md) | High | Self-update state machine | OpenHop Repeater Web API | An update install can overlap a version check and be reported idle while still running |
| 🟠 [BUG-021](findings/BUG-021-a-version-result-from-the-old-update-channel-can-be-shown-as-the-result-for-a-new-channel.md) | Medium | Self-update channel state | OpenHop Repeater Web API | A version result from the old update channel can be shown as the result for a new channel |
| 🟠 [BUG-022](findings/BUG-022-update-channel-persistence-failure-is-hidden-behind-a-success-response.md) | Medium | Self-update persistence / UI contract | OpenHop Repeater Web API | Update-channel persistence failure is hidden behind a success response |
| 🔴 [BUG-023](findings/BUG-023-a-failed-admin-password-save-still-changes-the-running-password.md) | High | Authentication / configuration transactions | OpenHop Repeater Web API | A failed admin-password save still changes the running password |
| 🟠 [BUG-024](findings/BUG-024-an-enhanced-raw-callback-is-invoked-twice-when-its-handler-raises.md) | Medium | Callback dispatch / side effects | OpenHop Core | An enhanced raw callback is invoked twice when its handler raises |
| 🟠 [BUG-025](findings/BUG-025-callbacks-returning-awaitables-from-synchronous-wrappers-are-silently-not-awaited.md) | Medium | Callback dispatch / async interoperability | OpenHop Core | Callbacks returning awaitables from synchronous wrappers are silently not awaited |
| 🔴 [BUG-027](findings/BUG-027-concurrent-message-persistence-can-remove-a-different-newer-message-from-memory.md) | High | Companion persistence / concurrency | OpenHop Core + OpenHop Repeater | Concurrent message persistence can remove a different, newer message from memory |

## Possible enhancements

| Finding | Area | Components | Summary |
|---|---|---|---|
| 🔧 [POSSIBLE-ENHANCEMENT-001](findings/POSSIBLE-ENHANCEMENT-001-use-one-typed-configuration-schema-across-yaml-api-openapi-and-ui.md) | Configuration architecture | OpenHop Repeater + Web UI | Possible enhancement — use one typed configuration schema across YAML, API, OpenAPI and UI |
| 🔧 [POSSIBLE-ENHANCEMENT-002](findings/POSSIBLE-ENHANCEMENT-002-introduce-a-transactional-configuration-update-service.md) | Configuration architecture | OpenHop Repeater | Possible enhancement — introduce a transactional configuration update service |
| 🔧 [POSSIBLE-ENHANCEMENT-003](findings/POSSIBLE-ENHANCEMENT-003-centralize-frontend-api-response-normalization.md) | Web UI architecture | OpenHop Repeater Web UI | Possible enhancement — centralize frontend API response normalization |
| 🔧 [POSSIBLE-ENHANCEMENT-004](findings/POSSIBLE-ENHANCEMENT-004-create-a-shared-airtime-snapshot-model.md) | Telemetry architecture | OpenHop Repeater + Web UI | Possible enhancement — create a shared airtime snapshot model |
| 🔧 [POSSIBLE-ENHANCEMENT-005](findings/POSSIBLE-ENHANCEMENT-005-define-a-radio-capability-adapter-instead-of-hasattr-branches.md) | Hardware abstraction | OpenHop Core + OpenHop Repeater | Possible enhancement — define a radio capability adapter instead of `hasattr` branches |
| 🔧 [POSSIBLE-ENHANCEMENT-006](findings/POSSIBLE-ENHANCEMENT-006-inject-a-clock-for-relative-timers.md) | Timekeeping and testing | OpenHop Core + OpenHop Repeater | Possible enhancement — inject a clock for relative timers |
| 🔧 [POSSIBLE-ENHANCEMENT-007](findings/POSSIBLE-ENHANCEMENT-007-split-apiendpoints-into-domain-controllers.md) | Maintainability | OpenHop Repeater | Possible enhancement — split `APIEndpoints` into domain controllers |
| 🔧 [POSSIBLE-ENHANCEMENT-008](findings/POSSIBLE-ENHANCEMENT-008-write-configuration-atomically-and-keep-a-last-known-good-copy.md) | Persistence robustness | OpenHop Repeater | Possible enhancement — write configuration atomically and keep a last-known-good copy |
| 🔧 [POSSIBLE-ENHANCEMENT-009](findings/POSSIBLE-ENHANCEMENT-009-share-advert-limiter-config-parsing-between-init-and-reload.md) | Code reuse | OpenHop Repeater | Possible enhancement — share advert-limiter config parsing between initialization and reload |
| 🔧 [POSSIBLE-ENHANCEMENT-010](findings/POSSIBLE-ENHANCEMENT-010-include-the-frontend-source-and-reproducible-build-metadata.md) | Build and reviewability | OpenHop Repeater Web UI | Possible enhancement — include frontend source and reproducible build metadata |
| 🔧 [POSSIBLE-ENHANCEMENT-011](findings/POSSIBLE-ENHANCEMENT-011-centralize-companion-delivery-outcomes-and-deduplication-commit.md) | Companion routing architecture | OpenHop Repeater | Possible enhancement — centralize companion delivery outcomes and deduplication commit |
| 🔧 [POSSIBLE-ENHANCEMENT-012](findings/POSSIBLE-ENHANCEMENT-012-share-one-duplicate-grouping-helper-for-normal-and-raw-receive-paths.md) | Packet history code reuse | OpenHop Repeater | Possible enhancement — share one duplicate-grouping helper for normal and raw receive paths |
| 🔧 [POSSIBLE-ENHANCEMENT-013](findings/POSSIBLE-ENHANCEMENT-013-parse-runtime-settings-once-for-both-initialization-and-live-reload.md) | Runtime configuration architecture | OpenHop Repeater | Possible enhancement — parse runtime settings once for both initialization and live reload |
| 🔧 [POSSIBLE-ENHANCEMENT-014](findings/POSSIBLE-ENHANCEMENT-014-replace-publication-booleans-with-a-typed-sink-policy.md) | Telemetry architecture | OpenHop Repeater | Possible enhancement — replace publication booleans with a typed sink policy |
| 🔧 [POSSIBLE-ENHANCEMENT-015](findings/POSSIBLE-ENHANCEMENT-015-use-one-callback-invocation-adapter-across-core.md) | Async callback code reuse | OpenHop Core | Possible enhancement — use one callback invocation adapter across Core |
| 🔧 [POSSIBLE-ENHANCEMENT-016](findings/POSSIBLE-ENHANCEMENT-016-model-self-update-work-as-versioned-jobs-instead-of-a-shared-state-string.md) | Self-update architecture | OpenHop Repeater Web API | Possible enhancement — model self-update work as versioned jobs instead of a shared state string |
| 🔧 [POSSIBLE-ENHANCEMENT-017](findings/POSSIBLE-ENHANCEMENT-017-add-bounded-backpressure-and-queue-metrics-to-the-storage-writer.md) | Storage reliability | OpenHop Repeater | Possible enhancement — add bounded backpressure and queue metrics to the storage writer |
| 🔧 [POSSIBLE-ENHANCEMENT-018](findings/POSSIBLE-ENHANCEMENT-018-use-an-acknowledged-outbox-for-companion-offline-delivery.md) | Companion reliability architecture | OpenHop Core + OpenHop Repeater | Possible enhancement — use an acknowledged outbox for companion offline delivery |

## Retracted, reclassified and merged reports

- [`BUG-002`](archive/retracted-reclassified-and-merged/BUG-002-configuration-screens-misread-the-standard-api-response-envelope.md) — retracted false positive.
- [`BUG-026`](archive/retracted-reclassified-and-merged/BUG-026-offline-companion-messages-are-dequeued-before-the-response-frame-is-accepted-for-transmission.md) — behavior verified, but reclassified as documented semantics and merged into `POSSIBLE-ENHANCEMENT-018`.
- [`POSSIBLE-ENHANCEMENT-019`](archive/retracted-reclassified-and-merged/POSSIBLE-ENHANCEMENT-019-generate-openapi-request-schemas-from-the-same-models-used-by-endpoints.md) — merged into `POSSIBLE-ENHANCEMENT-001`.
- [`POSSIBLE-ENHANCEMENT-020`](archive/retracted-reclassified-and-merged/POSSIBLE-ENHANCEMENT-020-give-message-queue-entries-stable-identities-and-removal-by-token.md) — merged into `BUG-027` and `POSSIBLE-ENHANCEMENT-018`.

## Verification material

- [`docs/REVERIFICATION-REPORT.md`](docs/REVERIFICATION-REPORT.md) — verdict on every original report
- [`docs/REVERIFICATION-CHECKS.py`](docs/REVERIFICATION-CHECKS.py) and [`docs/REVERIFICATION-CHECK-OUTPUT.txt`](docs/REVERIFICATION-CHECK-OUTPUT.txt)
- [`docs/ENHANCEMENT-PREMISE-CHECKS.py`](docs/ENHANCEMENT-PREMISE-CHECKS.py) and [`docs/ENHANCEMENT-PREMISE-CHECK-OUTPUT.txt`](docs/ENHANCEMENT-PREMISE-CHECK-OUTPUT.txt)
- [`docs/EVIDENCE-EXCERPT-VALIDATION.py`](docs/EVIDENCE-EXCERPT-VALIDATION.py) and [`docs/EVIDENCE-EXCERPT-VALIDATION-OUTPUT.txt`](docs/EVIDENCE-EXCERPT-VALIDATION-OUTPUT.txt)
- [`docs/CORE-TEST-OUTPUT.txt`](docs/CORE-TEST-OUTPUT.txt), [`docs/REPEATER-TEST-OUTPUT.txt`](docs/REPEATER-TEST-OUTPUT.txt) and collection summaries
- [`docs/UI-SOURCE-EXCERPTS.md`](docs/UI-SOURCE-EXCERPTS.md)
- [`docs/FILE-REVIEW-MATRIX.md`](docs/FILE-REVIEW-MATRIX.md)
- [`docs/PLAN-VALIDATION.md`](docs/PLAN-VALIDATION.md)
- [`MANIFEST.sha256`](MANIFEST.sha256)

## Implementation plans

Every active report links to `implementation-plans/<finding>/implementation_plan.md`. These are review-oriented plans, not ready-to-apply patches. The index contains **25 defect plans** and **18 possible-enhancement plans**.

- [`implementation-plans/README.md`](implementation-plans/README.md)
