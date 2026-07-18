# BUG-033 — KISS connection state remains healthy after initialization or worker failure

[← Audit index](../README.md)

> Triple-verification verdict: **confirmed against the supplied snapshots**. This report was included only after three independent checks passed.

| Field | Value |
|---|---|
| Classification | **Confirmed defect** |
| Severity | 🔴 **High** |
| Confidence | **Triple-verified** |
| Area | KISS connection lifecycle |
| Components | OpenHop Core |
| Audit date | 2026-07-17 |

## TL;DR

The adapter marks itself connected and starts worker threads before auto-configuration finishes. If configuration fails, it returns `False` without cleanup. A TX worker exception also exits without clearing connection state. The context manager ignores a false `connect()` result and still enters.

## Expected behavior

A failed initialization or dead transport worker must atomically transition the adapter to disconnected, close resources, and prevent further queue acceptance until reconnection.

## Required direction

1. Make `connect()` transactional: clean up serial/thread state on every failure after opening.
2. Have worker fatal exits mark the connection unhealthy and trigger one controlled reconnect/notification path.
3. Make `__enter__` raise when `connect()` returns false.

## Triple verification

| Method | Check | Result | Observation |
|---:|---|---|---|
| 1 | Auto-config failure | **Passed** | `connect()` returns false while connected state, open serial and started threads remain. |
| 2 | TX-worker failure | **Passed** | The worker exits but `is_connected()` stays true and accepts another queued frame. |
| 3 | Context manager | **Passed** | `with radio:` enters despite `connect()` returning false. |

The executable checks are preserved under [`docs/triple-verification/`](../docs/triple-verification/) and were rerun from clean Python processes for this edition.

## Implementation plan

See [`implementation-plans/BUG-033/implementation_plan.md`](../implementation-plans/BUG-033/implementation_plan.md).

## Source evidence

### Evidence 1: `src/openhop_core/hardware/kiss_serial_wrapper.py` lines 134–184

[Open source path](https://github.com/openhop-dev/openhop_core/blob/dev/src/openhop_core/hardware/kiss_serial_wrapper.py#L134-L184)

```text
  134 |     def connect(self) -> bool:
  135 |         """
  136 |         Connect to serial port and start communication threads
  137 | 
  138 |         Returns:
  139 |             True if connection successful, False otherwise
  140 |         """
  141 |         try:
  142 |             self.serial_conn = serial.Serial(
  143 |                 port=self.port,
  144 |                 baudrate=self.baudrate,
  145 |                 # Sole reader is _rx_worker (short blocking read); cap the port timeout so it
  146 |                 # releases the GIL while idle yet stays shutdown-responsive.
  147 |                 timeout=min(self.timeout, RX_READ_TIMEOUT_S),
  148 |                 bytesize=serial.EIGHTBITS,
  149 |                 parity=serial.PARITY_NONE,
  150 |                 stopbits=serial.STOPBITS_ONE,
  151 |             )
  152 | 
  153 |             self.is_connected = True
  154 |             self.stop_event.clear()
  155 | 
  156 |             # Start communication threads
  157 |             self.rx_thread = threading.Thread(target=self._rx_worker, daemon=True)
  158 |             self.tx_thread = threading.Thread(target=self._tx_worker, daemon=True)
  159 | 
  160 |             self.rx_thread.start()
  161 |             self.tx_thread.start()
  162 | 
  163 |             logger.info(f"KISS serial connected to {self.port} at {self.baudrate} baud")
  164 | 
  165 |             # Auto-configure if requested
  166 |             if self.auto_configure:
  167 |                 if not self.configure_radio_and_enter_kiss():
  168 |                     logger.warning("Auto-configuration failed, KISS mode not active")
  169 |                     return False
  170 | 
  171 |             return True
  172 | 
  173 |         except Exception as e:
  174 |             logger.error(f"Failed to connect to {self.port}: {e}")
  175 |             self.is_connected = False
  176 |             return False
  177 | 
  178 |     def disconnect(self):
  179 |         """Disconnect from serial port and stop threads"""
  180 |         self.is_connected = False
  181 |         self.stop_event.set()
  182 | 
  183 |         # Wait for threads to finish
  184 |         if self.rx_thread and self.rx_thread.is_alive():
```
### Evidence 2: `src/openhop_core/hardware/kiss_serial_wrapper.py` lines 747–779

[Open source path](https://github.com/openhop-dev/openhop_core/blob/dev/src/openhop_core/hardware/kiss_serial_wrapper.py#L747-L779)

```text
  747 |     def _tx_worker(self):
  748 |         """Background thread for sending data"""
  749 |         while not self.stop_event.is_set() and self.is_connected:
  750 |             try:
  751 |                 if self.tx_buffer:
  752 |                     # Get frame from buffer
  753 |                     frame = self.tx_buffer.popleft()
  754 | 
  755 |                     # Send via serial
  756 |                     if self.serial_conn and self.serial_conn.is_open:
  757 |                         self.serial_conn.write(frame)
  758 |                         self.serial_conn.flush()
  759 | 
  760 |                         self.stats["frames_sent"] += 1
  761 |                         self.stats["bytes_sent"] += len(frame)
  762 |                     else:
  763 |                         logger.warning("Serial connection not open or not available")
  764 |                 else:
  765 |                     # Short sleep when no data to send
  766 |                     threading.Event().wait(0.01)
  767 | 
  768 |             except Exception as e:
  769 |                 if self.is_connected:  # Only log if we expect to be connected
  770 |                     logger.error(f"TX worker error: {e}")
  771 |                 break
  772 | 
  773 |     def __enter__(self):
  774 |         """Context manager entry"""
  775 |         self.connect()
  776 |         return self
  777 | 
  778 |     def __exit__(self, exc_type, exc_val, exc_tb):
  779 |         """Context manager exit"""
```
### Evidence 3: `src/openhop_core/hardware/kiss_serial_wrapper.py` lines 772–781

[Open source path](https://github.com/openhop-dev/openhop_core/blob/dev/src/openhop_core/hardware/kiss_serial_wrapper.py#L772-L781)

```text
  772 | 
  773 |     def __enter__(self):
  774 |         """Context manager entry"""
  775 |         self.connect()
  776 |         return self
  777 | 
  778 |     def __exit__(self, exc_type, exc_val, exc_tb):
  779 |         """Context manager exit"""
  780 |         self.disconnect()
  781 | 
```

