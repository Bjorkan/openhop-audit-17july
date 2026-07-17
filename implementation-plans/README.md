# Implementation plans

These planning documents replace the former `.patch` sketches. They are intended to help a maintainer implement and review each finding safely; they are not guaranteed drop-in code changes.

Each plan includes:

- affected repositories and source files;
- required implementation work packages;
- decisions and assumptions to verify;
- focused, integration and failure-path tests;
- compatibility, rollout and rollback considerations;
- a concrete definition of done.

| Finding | Classification | Summary | Components |
|---|---|---|---|
| [BUG-001](BUG-001/implementation_plan.md) | Confirmed defect | Duty-cycle budget usage is presented as actual duty cycle | OpenHop Repeater + Web UI |
| [BUG-002](BUG-002/implementation_plan.md) | Confirmed defect | Configuration screens misread the standard API response envelope | OpenHop Repeater Web UI |
| [BUG-003](BUG-003/implementation_plan.md) | Confirmed defect | Live duty-cycle limit changes do not update the enforced limit | OpenHop Repeater |
| [BUG-004](BUG-004/implementation_plan.md) | Confirmed defect | Live radio changes leave airtime estimation on the old modulation | OpenHop Core + OpenHop Repeater |
| [BUG-005](BUG-005/implementation_plan.md) | Confirmed defect | SX1262 live radio updates omit transmit power | OpenHop Core + OpenHop Repeater |
| [BUG-006](BUG-006/implementation_plan.md) | Confirmed defect | Adaptive advert thresholds saved by the UI are ignored | OpenHop Repeater + Web UI |
| [BUG-007](BUG-007/implementation_plan.md) | Confirmed defect | Advert-rate-limit update reports immediate success after save or live-update failure | OpenHop Repeater |
| [BUG-008](BUG-008/implementation_plan.md) | Confirmed defect | Configuration export cannot be fully restored by configuration import | OpenHop Repeater + Web UI |
| [BUG-009](BUG-009/implementation_plan.md) | Confirmed defect | Configuration import reports success even when persistence fails | OpenHop Repeater + Web UI |
| [BUG-010](BUG-010/implementation_plan.md) | Confirmed defect | Rejected multi-field configuration requests leave partial in-memory changes | OpenHop Repeater |
| [BUG-011](BUG-011/implementation_plan.md) | Confirmed defect | GPS clock corrections can reset rolling airtime and rate-limit windows | OpenHop Repeater |
| [BUG-012](BUG-012/implementation_plan.md) | Confirmed defect | Quick mode and duty controls are volatile while the terminal labels them persisted | OpenHop Repeater + Web UI |
| [BUG-013](BUG-013/implementation_plan.md) | Confirmed defect | Failed companion deliveries are recorded as successfully delivered | OpenHop Repeater |
| [BUG-014](BUG-014/implementation_plan.md) | Confirmed defect | A failing companion bridge can shadow another local identity with the same destination hash | OpenHop Repeater |
| [BUG-015](BUG-015/implementation_plan.md) | Confirmed defect | Invalid packets are published to MQTT despite an explicit suppression request | OpenHop Repeater |
| [BUG-016](BUG-016/implementation_plan.md) | Confirmed defect | The raw duplicate path bypasses the configured per-packet duplicate cap | OpenHop Repeater |
| [BUG-017](BUG-017/implementation_plan.md) | Confirmed defect | Live reload can silently reduce the packet deduplication window from one hour to one minute | OpenHop Repeater |
| [BUG-018](BUG-018/implementation_plan.md) | Confirmed defect | `update_nested()` replaces sibling configuration instead of updating one deep value | OpenHop Repeater |
| [BUG-019](BUG-019/implementation_plan.md) | Confirmed defect | The OpenAPI duty-cycle request schema does not match the implemented endpoint | OpenHop Repeater |
| [BUG-020](BUG-020/implementation_plan.md) | Confirmed defect | An update install can overlap a version check and be reported idle while still running | OpenHop Repeater Web API |
| [BUG-021](BUG-021/implementation_plan.md) | Confirmed defect | A version result from the old update channel can be shown as the result for a new channel | OpenHop Repeater Web API |
| [BUG-022](BUG-022/implementation_plan.md) | Confirmed defect | Update-channel persistence failure is hidden behind a success response | OpenHop Repeater Web API |
| [BUG-023](BUG-023/implementation_plan.md) | Confirmed defect | A failed admin-password save still changes the running password | OpenHop Repeater Web API |
| [BUG-024](BUG-024/implementation_plan.md) | Confirmed defect | An enhanced raw callback is invoked twice when its handler raises | OpenHop Core |
| [BUG-025](BUG-025/implementation_plan.md) | Confirmed defect | Callbacks returning awaitables from synchronous wrappers are silently not awaited | OpenHop Core |
| [BUG-026](BUG-026/implementation_plan.md) | Confirmed defect | Offline companion messages are dequeued before the response frame is accepted for transmission | OpenHop Core + OpenHop Repeater |
| [BUG-027](BUG-027/implementation_plan.md) | Confirmed defect | Concurrent message persistence can remove a different, newer message from memory | OpenHop Core + OpenHop Repeater |
| [POSSIBLE-ENHANCEMENT-001](POSSIBLE-ENHANCEMENT-001/implementation_plan.md) | Possible enhancement | Possible enhancement — use one typed configuration schema across YAML, API, OpenAPI and UI | OpenHop Repeater + Web UI |
| [POSSIBLE-ENHANCEMENT-002](POSSIBLE-ENHANCEMENT-002/implementation_plan.md) | Possible enhancement | Possible enhancement — introduce a transactional configuration update service | OpenHop Repeater |
| [POSSIBLE-ENHANCEMENT-003](POSSIBLE-ENHANCEMENT-003/implementation_plan.md) | Possible enhancement | Possible enhancement — centralize frontend API response normalization | OpenHop Repeater Web UI |
| [POSSIBLE-ENHANCEMENT-004](POSSIBLE-ENHANCEMENT-004/implementation_plan.md) | Possible enhancement | Possible enhancement — create a shared airtime snapshot model | OpenHop Repeater + Web UI |
| [POSSIBLE-ENHANCEMENT-005](POSSIBLE-ENHANCEMENT-005/implementation_plan.md) | Possible enhancement | Possible enhancement — define a radio capability adapter instead of `hasattr` branches | OpenHop Core + OpenHop Repeater |
| [POSSIBLE-ENHANCEMENT-006](POSSIBLE-ENHANCEMENT-006/implementation_plan.md) | Possible enhancement | Possible enhancement — inject a clock for relative timers | OpenHop Core + OpenHop Repeater |
| [POSSIBLE-ENHANCEMENT-007](POSSIBLE-ENHANCEMENT-007/implementation_plan.md) | Possible enhancement | Possible enhancement — split `APIEndpoints` into domain controllers | OpenHop Repeater |
| [POSSIBLE-ENHANCEMENT-008](POSSIBLE-ENHANCEMENT-008/implementation_plan.md) | Possible enhancement | Possible enhancement — write configuration atomically and keep a last-known-good copy | OpenHop Repeater |
| [POSSIBLE-ENHANCEMENT-009](POSSIBLE-ENHANCEMENT-009/implementation_plan.md) | Possible enhancement | Possible enhancement — share advert-limiter config parsing between initialization and reload | OpenHop Repeater |
| [POSSIBLE-ENHANCEMENT-010](POSSIBLE-ENHANCEMENT-010/implementation_plan.md) | Possible enhancement | Possible enhancement — include frontend source and reproducible build metadata | OpenHop Repeater Web UI |
| [POSSIBLE-ENHANCEMENT-011](POSSIBLE-ENHANCEMENT-011/implementation_plan.md) | Possible enhancement | Possible enhancement — centralize companion delivery outcomes and deduplication commit | OpenHop Repeater |
| [POSSIBLE-ENHANCEMENT-012](POSSIBLE-ENHANCEMENT-012/implementation_plan.md) | Possible enhancement | Possible enhancement — share one duplicate-grouping helper for normal and raw receive paths | OpenHop Repeater |
| [POSSIBLE-ENHANCEMENT-013](POSSIBLE-ENHANCEMENT-013/implementation_plan.md) | Possible enhancement | Possible enhancement — parse runtime settings once for both initialization and live reload | OpenHop Repeater |
| [POSSIBLE-ENHANCEMENT-014](POSSIBLE-ENHANCEMENT-014/implementation_plan.md) | Possible enhancement | Possible enhancement — replace publication booleans with a typed sink policy | OpenHop Repeater |
| [POSSIBLE-ENHANCEMENT-015](POSSIBLE-ENHANCEMENT-015/implementation_plan.md) | Possible enhancement | Possible enhancement — use one callback invocation adapter across Core | OpenHop Core |
| [POSSIBLE-ENHANCEMENT-016](POSSIBLE-ENHANCEMENT-016/implementation_plan.md) | Possible enhancement | Possible enhancement — model self-update work as versioned jobs instead of a shared state string | OpenHop Repeater Web API |
| [POSSIBLE-ENHANCEMENT-017](POSSIBLE-ENHANCEMENT-017/implementation_plan.md) | Possible enhancement | Possible enhancement — add bounded backpressure and queue metrics to the storage writer | OpenHop Repeater |
| [POSSIBLE-ENHANCEMENT-018](POSSIBLE-ENHANCEMENT-018/implementation_plan.md) | Possible enhancement | Possible enhancement — use an acknowledged outbox for companion offline delivery | OpenHop Core + OpenHop Repeater |
| [POSSIBLE-ENHANCEMENT-019](POSSIBLE-ENHANCEMENT-019/implementation_plan.md) | Possible enhancement | Possible enhancement — generate OpenAPI request schemas from the same models used by endpoints | OpenHop Repeater |
| [POSSIBLE-ENHANCEMENT-020](POSSIBLE-ENHANCEMENT-020/implementation_plan.md) | Possible enhancement | Possible enhancement — give message-queue entries stable identities and removal by token | OpenHop Core + OpenHop Repeater |
