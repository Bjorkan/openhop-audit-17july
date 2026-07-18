# BUG-029 — Successful KISS queueing is reported as a transmission failure

[← Audit index](../README.md)

> Triple-verification verdict: **confirmed against the supplied snapshots**. This report was included only after three independent checks passed.

| Field | Value |
|---|---|
| Classification | **Confirmed defect** |
| Severity | 🟠 **Medium** |
| Confidence | **Triple-verified** |
| Area | Transmission result contract |
| Components | OpenHop Core |
| Audit date | 2026-07-17 |

## TL;DR

The abstract radio contract permits a successful send to return `None`, and the KISS adapter does exactly that after accepting a frame. `Dispatcher` interprets the same `None` as failure, returns `False`, and skips successful-send callbacks even though the frame is queued for transmission.

## Expected behavior

A successful transport submission must have one unambiguous result shared by all radio implementations and `Dispatcher`.

## Required direction

1. Replace the ambiguous `dict | None` result with a typed result carrying success plus optional metadata, or make every successful adapter return a metadata mapping.
2. Update KISS and all other radio implementations atomically with the dispatcher interpretation.
3. Ensure sent callbacks and accounting execute exactly once after an accepted submission.

## Triple verification

| Method | Check | Result | Observation |
|---|---|---|---|
| Static runtime trace | Adapter/dispatcher return contract | **Passed** | The base contract and KISS implementation permit/return `None`; Dispatcher treats any falsy metadata as send failure. |
| Executable reproduction | Direct adapter path | **Passed** | KISS accepts and queues the frame, returns `None`, and raises no error. |
| Active falsification | Dispatcher integration countercheck | **Passed** | The same accepted frame produces `False` from `send_packet`; no wrapper normalizes successful queueing. |

The executable checks are preserved under [`docs/triple-verification/`](../docs/triple-verification/) and were rerun from clean Python processes for this edition. The third row is an explicit falsification/countercheck that searches for a guard, alternate adapter, normalization, documented contract or unreachable-state explanation that would invalidate the finding.

## Implementation plan

See [`implementation-plans/BUG-029/implementation_plan.md`](../implementation-plans/BUG-029/implementation_plan.md).

## Source evidence

### Evidence 1: `src/openhop_core/hardware/base.py` lines 8–16

[Open source path](https://github.com/openhop-dev/openhop_core/blob/dev/src/openhop_core/hardware/base.py#L8-L16)

```text
    8 |         pass
    9 | 
   10 |     @abstractmethod
   11 |     async def send(self, data: bytes):
   12 |         """Send a packet asynchronously. Returns transmission metadata dict or None."""
   13 |         pass
   14 | 
   15 |     @abstractmethod
   16 |     async def wait_for_rx(self) -> bytes:
```
### Evidence 2: `src/openhop_core/hardware/kiss_serial_wrapper.py` lines 486–503

[Open source path](https://github.com/openhop-dev/openhop_core/blob/dev/src/openhop_core/hardware/kiss_serial_wrapper.py#L486-L503)

```text
  486 | 
  487 |     async def send(self, data: bytes) -> None:
  488 |         """
  489 |         Send data via KISS TNC. Returns None (no metadata available).
  490 | 
  491 |         Args:
  492 |             data: Data to send
  493 | 
  494 |         Raises:
  495 |             Exception: If send fails
  496 |         """
  497 |         success = self.send_frame(data)
  498 |         if not success:
  499 |             raise Exception("Failed to send frame via KISS TNC")
  500 |         return None
  501 | 
  502 |     async def wait_for_rx(self) -> bytes:
  503 |         """
```
### Evidence 3: `src/openhop_core/node/dispatcher.py` lines 889–915

[Open source path](https://github.com/openhop-dev/openhop_core/blob/dev/src/openhop_core/node/dispatcher.py#L889-L915)

```text
  889 |         # ------------------------------------------------------------------ #
  890 |         self.state = DispatcherState.TRANSMIT
  891 |         raw = packet.write_to()
  892 |         tx_metadata = None
  893 |         try:
  894 |             tx_metadata = await self.radio.send(raw)
  895 |         except Exception as e:
  896 |             self._log(f"Radio transmit error: {e}")
  897 |             self.state = DispatcherState.IDLE
  898 |             return False
  899 |         if tx_metadata is None:
  900 |             self._log("Radio transmit returned no confirmation metadata")
  901 |             self.state = DispatcherState.IDLE
  902 |             return False
  903 |         # Spend the airtime budget on the completed transmit (client-repeat only).
  904 |         if self._client_repeat_enabled:
  905 |             self._debit_tx_budget(packet)
  906 |         # Log what we sent
  907 |         type_name = PAYLOAD_TYPES.get(payload_type, f"UNKNOWN_{payload_type}")
  908 |         route_name = ROUTE_TYPES.get(packet.get_route_type(), f"UNKNOWN_{packet.get_route_type()}")
  909 |         self._log(f"TX {packet.get_raw_length()} bytes (type={type_name}, route={route_name})")
  910 | 
  911 |         # Store metadata on packet for access by handlers
  912 |         if tx_metadata:
  913 |             packet._tx_metadata = tx_metadata
  914 | 
  915 |         if self.packet_sent_callback:
```

