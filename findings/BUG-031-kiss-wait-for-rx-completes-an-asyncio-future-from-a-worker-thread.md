# BUG-031 — KISS `wait_for_rx()` completes an asyncio future from the serial worker thread

[← Audit index](../README.md)

> Triple-verification verdict: **confirmed against the supplied snapshots**. This report was included only after three independent checks passed.

| Field | Value |
|---|---|
| Classification | **Confirmed defect** |
| Severity | 🔴 **High** |
| Confidence | **Triple-verified** |
| Area | Threading / asyncio interoperability |
| Components | OpenHop Core |
| Audit date | 2026-07-17 |

## TL;DR

The serial RX worker invokes `on_frame_received` synchronously. `wait_for_rx()` temporarily installs a callback that calls `Future.set_result()` directly, crossing from the worker thread into the event loop without `call_soon_threadsafe`. Debug mode raises, and normal mode can leave the waiter asleep until another loop event occurs.

## Expected behavior

Worker threads must transfer completion to the owning event loop using its thread-safe scheduling API.

## Required direction

1. Capture the running loop in `wait_for_rx()` and use `loop.call_soon_threadsafe` to complete the future.
2. Make callback replacement/restoration concurrency-safe and avoid one waiter overwriting a persistent callback.
3. Prefer a thread-safe asyncio queue or a fan-out receive dispatcher for multiple consumers.

## Triple verification

| Method | Check | Result | Observation |
|---|---|---|---|
| Static runtime trace | Worker callback to asyncio waiter | **Passed** | The serial worker invokes the RX callback directly, and that callback calls `future.set_result` without a thread-safe event-loop hop. |
| Executable reproduction | Debug event loop | **Passed** | The real wait path raises Python’s non-thread-safe event-loop `RuntimeError`. |
| Active falsification | Release-loop countercheck | **Passed** | With debug checks absent, the waiter still does not resume until an unrelated thread-safe nudge wakes the loop, so the issue is not debug-only. |

The executable checks are preserved under [`docs/triple-verification/`](../docs/triple-verification/) and were rerun from clean Python processes for this edition. The third row is an explicit falsification/countercheck that searches for a guard, alternate adapter, normalization, documented contract or unreachable-state explanation that would invalidate the finding.

## Implementation plan

See [`implementation-plans/BUG-031/implementation_plan.md`](../implementation-plans/BUG-031/implementation_plan.md).

## Source evidence

### Evidence 1: `src/openhop_core/hardware/kiss_serial_wrapper.py` lines 502–536

[Open source path](https://github.com/openhop-dev/openhop_core/blob/dev/src/openhop_core/hardware/kiss_serial_wrapper.py#L502-L536)

```text
  502 |     async def wait_for_rx(self) -> bytes:
  503 |         """
  504 |         Wait for a packet to be received asynchronously
  505 | 
  506 |         Returns:
  507 |             Received packet data
  508 |         """
  509 |         # Create a future to wait for the next received frame
  510 |         future = asyncio.Future()
  511 | 
  512 |         # Store the original callback
  513 |         original_callback = self.on_frame_received
  514 | 
  515 |         # Set a temporary callback that completes the future
  516 |         def temp_callback(data: bytes):
  517 |             if not future.done():
  518 |                 future.set_result(data)
  519 |             # Restore original callback if it exists
  520 |             if original_callback:
  521 |                 try:
  522 |                     original_callback(data)
  523 |                 except Exception as e:
  524 |                     logger.error(f"Error in original callback: {e}")
  525 | 
  526 |         self.on_frame_received = temp_callback
  527 | 
  528 |         try:
  529 |             # Wait for the next frame
  530 |             data = await future
  531 |             return data
  532 |         finally:
  533 |             # Restore original callback
  534 |             self.on_frame_received = original_callback
  535 | 
  536 |     def sleep(self):
```
### Evidence 2: `src/openhop_core/hardware/kiss_serial_wrapper.py` lines 709–725

[Open source path](https://github.com/openhop-dev/openhop_core/blob/dev/src/openhop_core/hardware/kiss_serial_wrapper.py#L709-L725)

```text
  709 |         data = bytes(self.rx_frame_buffer[1:])
  710 | 
  711 |         if cmd == KISS_CMD_DATA:
  712 |             # Data frame - emit to callback
  713 |             if self.on_frame_received and len(data) > 0:
  714 |                 self.stats["frames_received"] += 1
  715 |                 self.stats["bytes_received"] += len(data)
  716 |                 try:
  717 |                     self.on_frame_received(data)
  718 |                 except Exception as e:
  719 |                     logger.error(f"Error in frame received callback: {e}")
  720 |         else:
  721 |             # Configuration command response
  722 |             logger.debug(f"Received KISS config command: cmd=0x{cmd:02X}, data={data.hex()}")
  723 | 
  724 |     def _rx_worker(self):
  725 |         """Background thread for receiving data"""
```
### Evidence 3: `src/openhop_core/hardware/kiss_serial_wrapper.py` lines 724–749

[Open source path](https://github.com/openhop-dev/openhop_core/blob/dev/src/openhop_core/hardware/kiss_serial_wrapper.py#L724-L749)

```text
  724 |     def _rx_worker(self):
  725 |         """Background thread for receiving data"""
  726 |         while not self.stop_event.is_set() and self.is_connected:
  727 |             try:
  728 |                 conn = self.serial_conn
  729 |                 if conn is None:
  730 |                     break
  731 |                 # Blocking read of >=1 byte: sleeps in the kernel (releasing the GIL) until
  732 |                 # data or the port timeout, instead of busy-polling. Then drain whatever else
  733 |                 # arrived and bulk-decode it in one pass.
  734 |                 chunk = conn.read(1)
  735 |                 if not chunk:
  736 |                     continue  # timeout with no data; loop re-checks stop_event
  737 |                 pending = conn.in_waiting
  738 |                 if pending:
  739 |                     chunk += conn.read(pending)
  740 |                 self._decode_kiss(chunk)
  741 | 
  742 |             except Exception as e:
  743 |                 if self.is_connected:  # Only log if we expect to be connected
  744 |                     logger.error(f"RX worker error: {e}")
  745 |                 break
  746 | 
  747 |     def _tx_worker(self):
  748 |         """Background thread for sending data"""
  749 |         while not self.stop_event.is_set() and self.is_connected:
```

