# File review matrix

## Repository totals

| Tree | Python files | Python lines | Review coverage |
|---|---:|---:|---|
| `openhop_core/src/openhop_core` | 88 | 30,625 | Indexed; hardware/configuration paths manually traced |
| `openhop_repeater/repeater` | 68 | 36,847 | Indexed; API, config, radio, airtime, adverts, storage, GPS and UI contracts manually traced |
| `repeater/web/html/assets` | 66 assets | Minified build output | String/contract tracing with exact byte offsets |

## Manual focus areas

| Area | Primary files | Review focus |
|---|---|---|
| Duty-cycle enforcement | `repeater/airtime.py`, `repeater/engine.py` | Runtime limits, units, rolling window, telemetry |
| Configuration persistence | `repeater/config_manager.py` | Save semantics, live reload, rollback and hardware application |
| Configuration API | `repeater/web/api_endpoints.py` | Validation order, response envelopes, backup/restore, quick controls |
| Radio hardware | `openhop_core/hardware/sx1262_wrapper.py`, `kiss_modem_wrapper.py`, USB/TCP wrappers | Capability differences and live application |
| Advert limiting | `repeater/handler_helpers/advert.py`, `config.yaml.example` | Config names, reload parity, thresholds, rate windows |
| GPS time | `repeater/data_acquisition/gps_service.py`, `repeater/config.py` | System-clock changes vs relative timers |
| Telemetry consumers | engine stats, Glass handler, storage collector | Naming and denominator consistency |
| Web UI | `Configuration-*.js`, `Terminal-*.js`, `index-*.js`, API client bundle | Response unwrapping and displayed state |
| Companion routing | `repeater/packet_router.py` | Authentication outcomes, one-byte hash collisions, delivery deduplication |
| Companion queues | Core frame-server transport/message commands, Repeater persistence subclass | Pop/enqueue ordering, persistence ownership, async interleavings |
| Callback dispatch | Core Dispatcher, handlers and Companion callbacks | Signature compatibility, awaitable handling, duplicate invocation |
| Self-update | `repeater/web/update_endpoints.py` | Worker ownership, state transitions, channel persistence and stale results |
| OpenAPI | `repeater/web/openapi.yaml` + endpoint parsers | Request field parity |

## Automated coverage

- Full project test suites.
- `compileall` on both Python source trees.
- OpenAPI contract checker.
- Focused cross-layer reproduction scripts included with the audit: 12 first-pass checks and 15 deep-review checks.

This matrix distinguishes automated indexing from manually traced paths; it does not claim that every line was semantically proven correct.
