# Claim verification matrix

| Claim | Evidence | Verification |
|---|---|---|
| Duty telemetry uses the wrong semantic label | AirtimeManager, engine stats, Glass/storage, compiled UI | Executable numeric reproduction + source trace |
| Live duty limit is stale | AirtimeManager constructor and ConfigManager live-update dispatch | Executable reproduction |
| Radio live update leaves airtime stale | ConfigManager radio path and AirtimeManager cached scalars | Executable reproduction |
| SX1262 TX power is omitted | ConfigManager configure branch + SX1262 method signatures | Executable fake-radio reproduction |
| Adaptive thresholds are ignored | YAML/API/UI key names vs AdvertHelper parser | Executable reproduction |
| Advert update can falsely succeed | Endpoint result construction | Executable mocked save failure |
| Export/import is not round-trip | Full export + import allowlist | Executable rejected-section reproduction |
| Import can falsely succeed | Ignored save result + duplicate save | Executable double-failure reproduction |
| Validation failure leaves mutation | Sequential endpoint mutation | Executable request reproduction |
| Clock jump resets limiter | GPS CLOCK_REALTIME setter + wall-clock airtime history | Executable clock-jump reproduction |
| Quick controls are volatile | Endpoint code + terminal compiled asset | Mock call trace + static bundle evidence |
| UI envelope handling is inconsistent | `_success` + compiled handlers | Static assertion against supplied bytes |
| Failed companion deliveries are deduplicated | PacketRouter fan-out and mark paths | Executable unauthenticated bridge reproduction |
| Companion exception shadows another local identity | Local candidate collision helper | Executable raising-bridge reproduction |
| Invalid packets still reach MQTT | Engine publication request + StorageCollector sink path | Executable mock-call reproduction |
| Raw duplicate cap is bypassed | Normal and raw duplicate grouping branches | Executable bounded-list reproduction |
| Reload changes cache TTL semantics | RepeaterHandler init and reload | Executable reload reproduction |
| Deep nested update clobbers siblings | ConfigManager dotted-path builder + shallow section update | Executable config reproduction |
| OpenAPI duty request is stale | OpenAPI schema + endpoint accepted keys | Static contract assertion |
| Check completion can overwrite install state | Updater transitions + worker completion | Executable state-machine reproduction |
| Old-channel result can populate new channel | Updater channel mutation + check worker | Executable stale-result reproduction |
| Channel save failure is reported as success | Updater persistence and endpoint response | Executable mocked persistence failure |
| Password save failure changes runtime credential | Auth endpoint mutation order | Executable save-failure reproduction |
| Enhanced callback is retried after handler error | Dispatcher compatibility fallback | Executable invocation-count reproduction |
| Returned callback awaitables are ignored | Dispatcher/Companion invocation helpers | Executable sync-wrapper reproduction |
| Offline message is popped before enqueue | Message sync command + transport queue | Executable QueueFull reproduction |
| Async persistence can pop the wrong message | SQLite await + positional pop_last | Executable interleaving reproduction |
