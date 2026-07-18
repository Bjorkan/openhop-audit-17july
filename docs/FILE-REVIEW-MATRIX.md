# File review matrix

## Repository totals

| Tree | Python files | Python lines | Review coverage |
|---|---:|---:|---|
| `openhop_core/src/openhop_core` | 89 | 31,125 | Indexed; hardware/configuration paths manually traced |
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
| Core client-repeat airtime budget | `src/openhop_core/node/dispatcher.py`, `tests/test_tx_budget.py` | Atomic admission, TX serialization, pacing, cancellation and concurrent sends |

## Automated coverage

- Full project test suites.
- `compileall` on both Python source trees.
- OpenAPI contract checker.
- Focused cross-layer reproduction scripts included with the audit, including 66 checks for BUG-028–BUG-049.

This matrix distinguishes automated indexing from manually traced paths; it does not claim that every line was semantically proven correct.


## Triple-verified deep-review extension

The following additional source surfaces were traced during BUG-028–BUG-049. Inclusion here means the file participated in at least one end-to-end trace; it does not imply every line in the file was audited.

| Repository | Path | Review scope |
|---|---|---|
| OpenHop Core | `src/openhop_core/hardware/wsradio.py` | Deep-review source trace and executable reproduction evidence |
| OpenHop Core | `src/openhop_core/node/dispatcher.py` | Deep-review source trace and executable reproduction evidence |
| OpenHop Core | `src/openhop_core/hardware/base.py` | Deep-review source trace and executable reproduction evidence |
| OpenHop Core | `src/openhop_core/hardware/kiss_serial_wrapper.py` | Deep-review source trace and executable reproduction evidence |
| OpenHop Core | `src/openhop_core/node/node.py` | Deep-review source trace and executable reproduction evidence |
| OpenHop Core | `src/openhop_core/hardware/tcp_radio.py` | Deep-review source trace and executable reproduction evidence |
| OpenHop Core | `src/openhop_core/hardware/usb_radio.py` | Deep-review source trace and executable reproduction evidence |
| OpenHop Repeater | `repeater/config_manager.py` | Deep-review source trace and executable reproduction evidence |
| OpenHop Core | `src/openhop_core/companion/base_send.py` | Deep-review source trace and executable reproduction evidence |
| OpenHop Core | `src/openhop_core/node/handlers/text.py` | Deep-review source trace and executable reproduction evidence |
| OpenHop Core | `src/openhop_core/node/handlers/login_response.py` | Deep-review source trace and executable reproduction evidence |
| OpenHop Core | `src/openhop_core/companion/frame_server/push.py` | Deep-review source trace and executable reproduction evidence |
| OpenHop Core | `src/openhop_core/companion/base_callbacks.py` | Deep-review source trace and executable reproduction evidence |
| OpenHop Repeater | `repeater/companion/bridge.py` | Deep-review source trace and executable reproduction evidence |
| OpenHop Core | `src/openhop_core/companion/base_config.py` | Deep-review source trace and executable reproduction evidence |
| OpenHop Repeater | `repeater/data_acquisition/websocket_handler.py` | Deep-review source trace and executable reproduction evidence |
| OpenHop Repeater | `repeater/data_acquisition/rrdtool_handler.py` | Deep-review source trace and executable reproduction evidence |
| OpenHop Repeater | `repeater/web/api_endpoints.py` | Deep-review source trace and executable reproduction evidence |
| OpenHop Repeater | `repeater/config.py` | Deep-review source trace and executable reproduction evidence |
| OpenHop Core | `src/openhop_core/hardware/sx1262_wrapper.py` | Deep-review source trace and executable reproduction evidence |
| OpenHop Core | `src/openhop_core/hardware/lora/LoRaRF/SX126x.py` | Deep-review source trace and executable reproduction evidence |
| OpenHop Repeater | `repeater/handler_helpers/mesh_cli.py` | Deep-review source trace and executable reproduction evidence |
| OpenHop Repeater | `tests/test_handler_helpers_mesh_cli.py` | Deep-review source trace and executable reproduction evidence |
| OpenHop Repeater | `repeater/handler_helpers/login.py` | Deep-review source trace and executable reproduction evidence |
| OpenHop Repeater | `config.yaml.example` | Deep-review source trace and executable reproduction evidence |
| OpenHop Repeater | `repeater/engine.py` | Deep-review source trace and executable reproduction evidence |
