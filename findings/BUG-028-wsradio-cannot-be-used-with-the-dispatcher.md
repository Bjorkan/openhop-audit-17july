# BUG-028 — `WsRadio` cannot be used with `Dispatcher` or `MeshNode`

[← Audit index](../README.md)

> Triple-verification verdict: **confirmed against the supplied snapshots**. This report was included only after three independent checks passed.

| Field | Value |
|---|---|
| Classification | **Confirmed defect** |
| Severity | 🔴 **High** |
| Confidence | **Triple-verified** |
| Area | Radio abstraction / construction |
| Components | OpenHop Core |
| Audit date | 2026-07-17 |

## TL;DR

`Dispatcher` unconditionally registers an RX callback, but `WsRadio` does not implement the required callback method. Constructing the documented radio through the normal node stack raises `AttributeError` before any connection attempt.

## Expected behavior

Every concrete `LoRaRadio` exposed by Core must satisfy the receive contract required by `Dispatcher`, or the dispatcher must explicitly support both callback and pull-based radios.

## Required direction

1. Define the receive-registration requirement in `LoRaRadio` and implement it in `WsRadio`, including dispatch from the WebSocket receive loop.
2. Alternatively introduce a capability adapter and make `Dispatcher` select a supported receive mode explicitly; do not silently skip reception.
3. Add construction and end-to-end receive tests for `WsRadio` through `MeshNode`.

## Triple verification

| Method | Check | Result | Observation |
|---|---|---|---|
| Static runtime trace | Radio/dispatcher construction contract | **Passed** | `WsRadio` has no `set_rx_callback`, while `Dispatcher.__init__` calls it unconditionally before any connection attempt. |
| Executable reproduction | Dispatcher construction | **Passed** | Creating `Dispatcher(WsRadio(...))` raises `AttributeError` through the real constructor. |
| Active falsification | Public `MeshNode` path | **Passed** | The public node wrapper reaches the same failure and contains no adapter, normalization or fallback that makes the state unreachable. |

The executable checks are preserved under [`docs/triple-verification/`](../docs/triple-verification/) and were rerun from clean Python processes for this edition. The third row is an explicit falsification/countercheck that searches for a guard, alternate adapter, normalization, documented contract or unreachable-state explanation that would invalidate the finding.

## Implementation plan

See [`implementation-plans/BUG-028/implementation_plan.md`](../implementation-plans/BUG-028/implementation_plan.md).

## Source evidence

### Evidence 1: `src/openhop_core/hardware/wsradio.py` lines 12–42

[Open source path](https://github.com/openhop-dev/openhop_core/blob/dev/src/openhop_core/hardware/wsradio.py#L12-L42)

```text
   12 | 
   13 | 
   14 | class WsRadio(LoRaRadio):
   15 |     def __init__(self, ip_address="192.168.0.33", port=81, timeout=30, radio_config=None):
   16 |         self.url = f"ws://{ip_address}:{port}"
   17 |         self.ws = None
   18 |         self.last_rssi = -99
   19 |         self.last_snr = 0.0
   20 |         self._connected = False
   21 |         self._last_tx_data = None  # Stores last transmitted packet
   22 |         self._last_tx_time = 0.0
   23 |         self._connection_lock = asyncio.Lock()  # Prevent concurrent connection attempts
   24 |         self._recv_lock = asyncio.Lock()  # Prevent concurrent recv calls
   25 |         self._reconnect_delay = 1.0  # Start with 1 second
   26 |         self._max_reconnect_delay = 30.0  # Max 30 seconds
   27 |         self._timeout = timeout
   28 | 
   29 |         # Store radio configuration
   30 |         self.radio_config = radio_config
   31 |         if radio_config:
   32 |             logger.info(
   33 |                 f"Radio config: freq={radio_config.frequency}MHz, "
   34 |                 f"power={radio_config.tx_power}dBm, bw={radio_config.bandwidth}kHz, "
   35 |                 f"sf={radio_config.spreading_factor}, cr={radio_config.coding_rate}, "
   36 |                 f"preamble={radio_config.preamble_length}"
   37 |             )
   38 | 
   39 |     async def _send_radio_config(self):
   40 |         """Send radio configuration to the WebSocket radio."""
   41 |         if not self.radio_config or not self.ws:
   42 |             return
```
### Evidence 2: `src/openhop_core/node/dispatcher.py` lines 173–184

[Open source path](https://github.com/openhop-dev/openhop_core/blob/dev/src/openhop_core/node/dispatcher.py#L173-L184)

```text
  173 |         # Let the node register for packet analysis if it wants
  174 |         self.packet_analysis_callback: Optional[Callable[[Any, bytes], None]] = None
  175 | 
  176 |         # Initialize fallback handler
  177 |         self._fallback_handler = None
  178 | 
  179 |         # Hook up the radio's receive callback - all radios should support this
  180 |         self.radio.set_rx_callback(self._on_packet_received)
  181 |         self._logger.info("Registered RX callback with radio")
  182 | 
  183 |     def set_contact_book(self, contact_book):
  184 |         """Set the contact book for decryption operations."""
```

