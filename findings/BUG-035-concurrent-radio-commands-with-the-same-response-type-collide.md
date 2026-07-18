# BUG-035 — Concurrent radio commands expecting the same response type overwrite one another

[← Audit index](../README.md)

> Triple-verification verdict: **confirmed against the supplied snapshots**. This report was included only after three independent checks passed.

| Field | Value |
|---|---|
| Classification | **Confirmed defect** |
| Severity | 🔴 **High** |
| Confidence | **Triple-verified** |
| Area | Radio protocol concurrency |
| Components | OpenHop Core |
| Audit date | 2026-07-17 |

## TL;DR

TCP and USB adapters correlate pending commands only by `expect_cmd`. Two concurrent commands waiting for the same response byte replace the same event/data entries. One request receives the response while the other times out or consumes mismatched state.

## Expected behavior

Every in-flight request must have exclusive, deterministic response ownership, or commands must be serialized when the wire protocol has no transaction ID.

## Required direction

1. Introduce a per-adapter command lock for protocols that cannot correlate parallel requests, or add request IDs if firmware supports them.
2. Never overwrite an existing waiter silently; reject/queue the second request.
3. Centralize this logic in a shared protocol helper used by TCP and USB.

## Triple verification

| Method | Check | Result | Observation |
|---|---|---|---|
| Static runtime trace | Response correlation ownership | **Passed** | Both TCP and USB adapters index pending waiters only by response command and provide no command-level serialization. |
| Executable reproduction | TCP overlapping commands | **Passed** | Two real command calls are sent; one receives data and the other times out after its waiter is overwritten. |
| Active falsification | Independent USB adapter | **Passed** | The same collision reproduces in the separate USB implementation, excluding a TCP-only transport artifact or wrapper guard. |

The executable checks are preserved under [`docs/triple-verification/`](../docs/triple-verification/) and were rerun from clean Python processes for this edition. The third row is an explicit falsification/countercheck that searches for a guard, alternate adapter, normalization, documented contract or unreachable-state explanation that would invalidate the finding.

## Implementation plan

See [`implementation-plans/BUG-035/implementation_plan.md`](../implementation-plans/BUG-035/implementation_plan.md).

## Source evidence

### Evidence 1: `src/openhop_core/hardware/tcp_radio.py` lines 159–171

[Open source path](https://github.com/openhop-dev/openhop_core/blob/dev/src/openhop_core/hardware/tcp_radio.py#L159-L171)

```text
  159 |         self.rx_callback: Optional[Callable[[bytes], None]] = None
  160 | 
  161 |         # Response synchronization
  162 |         self._response_events: dict[int, asyncio.Event] = {}
  163 |         self._response_data: dict[int, Optional[bytes]] = {}
  164 |         self._response_lock = threading.Lock()
  165 | 
  166 |         # TX lock
  167 |         self._tx_lock = asyncio.Lock()
  168 | 
  169 |         # Stats
  170 |         self._tx_count = 0
  171 |         self._rx_count = 0
```
### Evidence 2: `src/openhop_core/hardware/tcp_radio.py` lines 887–930

[Open source path](https://github.com/openhop-dev/openhop_core/blob/dev/src/openhop_core/hardware/tcp_radio.py#L887-L930)

```text
  887 |     async def _send_command(
  888 |         self,
  889 |         cmd: int,
  890 |         payload: bytes,
  891 |         expect_cmd: int,
  892 |         timeout: float = 5.0,
  893 |     ) -> Optional[bytes]:
  894 |         if self._sock is None:
  895 |             return None
  896 | 
  897 |         if self._event_loop is None:
  898 |             try:
  899 |                 self._event_loop = asyncio.get_running_loop()
  900 |             except RuntimeError:
  901 |                 pass
  902 | 
  903 |         evt = asyncio.Event()
  904 |         with self._response_lock:
  905 |             self._response_events[expect_cmd] = evt
  906 |             self._response_data.pop(expect_cmd, None)
  907 | 
  908 |         try:
  909 |             frame = build_frame(cmd, payload)
  910 |             try:
  911 |                 self._sock_write(frame)
  912 |             except (OSError, ConnectionError) as e:
  913 |                 logger.error(f"TCP write failed: {e}")
  914 |                 return None
  915 | 
  916 |             try:
  917 |                 await asyncio.wait_for(evt.wait(), timeout=timeout)
  918 |             except asyncio.TimeoutError:
  919 |                 logger.warning(
  920 |                     f"Timeout: cmd=0x{cmd:02X} → expected 0x{expect_cmd:02X}"
  921 |                 )
  922 |                 return None
  923 | 
  924 |             return self._response_data.get(expect_cmd)
  925 | 
  926 |         finally:
  927 |             with self._response_lock:
  928 |                 self._response_events.pop(expect_cmd, None)
  929 |                 self._response_data.pop(expect_cmd, None)
  930 | 
```
### Evidence 3: `src/openhop_core/hardware/usb_radio.py` lines 951–996

[Open source path](https://github.com/openhop-dev/openhop_core/blob/dev/src/openhop_core/hardware/usb_radio.py#L951-L996)

```text
  951 |     async def _send_command(
  952 |         self,
  953 |         cmd: int,
  954 |         payload: bytes,
  955 |         expect_cmd: int,
  956 |         timeout: float = 5.0,
  957 |     ) -> Optional[bytes]:
  958 |         """Send a command frame and wait for a specific response frame."""
  959 |         if not self._serial or not self._serial.is_open:
  960 |             return None
  961 | 
  962 |         # Ensure event loop is captured
  963 |         if self._event_loop is None:
  964 |             try:
  965 |                 self._event_loop = asyncio.get_running_loop()
  966 |             except RuntimeError:
  967 |                 pass
  968 | 
  969 |         # Register response expectation
  970 |         evt = asyncio.Event()
  971 |         with self._response_lock:
  972 |             self._response_events[expect_cmd] = evt
  973 |             self._response_data.pop(expect_cmd, None)
  974 | 
  975 |         try:
  976 |             frame = build_frame(cmd, payload)
  977 |             self._serial.write(frame)
  978 |             self._serial.flush()
  979 | 
  980 |             try:
  981 |                 await asyncio.wait_for(evt.wait(), timeout=timeout)
  982 |             except asyncio.TimeoutError:
  983 |                 logger.warning(
  984 |                     f"Timeout: cmd=0x{cmd:02X} → expected 0x{expect_cmd:02X}"
  985 |                 )
  986 |                 return None
  987 | 
  988 |             return self._response_data.get(expect_cmd)
  989 | 
  990 |         finally:
  991 |             with self._response_lock:
  992 |                 self._response_events.pop(expect_cmd, None)
  993 |                 self._response_data.pop(expect_cmd, None)
  994 | 
  995 |     async def _perform_cad(self, timeout: float = 1.0) -> bool:
  996 |         """Perform Channel Activity Detection. Returns True if busy."""
```

