# BUG-025 — Callbacks returning awaitables from synchronous wrappers are silently not awaited

[← Audit index](../README.md)

> Triple-verification verdict: **confirmed against the supplied snapshots**. The finding survived an independent static runtime trace, executable reproduction and active falsification pass on 18 July 2026.

| Field | Value |
|---|---|
| Classification | **Confirmed defect** |
| Severity | **Medium** |
| Confidence | **Triple-verified** |
| Area | Callback dispatch / async interoperability |
| Components | OpenHop Core |
| Audit date | 2026-07-17 |
| Independent recheck | 2026-07-18 |
| Status | Open in supplied snapshot |

## TL;DR

Multiple callback helpers decide whether to await by checking `inspect.iscoroutinefunction(callback)`. A normal callable that returns an awaitable is called but its coroutine is discarded.

## What happens now

This affects callable objects with async `__call__`, decorated async functions whose outer wrapper is synchronous, and intentionally synchronous adapters returning an awaitable. Type annotations allow `Awaitable | None`, and another helper in the same module already implements the correct “call, then inspect result” pattern.

## Expected behaviour / proposed direction

Callback invocation should always call once, inspect the returned object and await it when `inspect.isawaitable(result)` is true.

## What needs to change

Introduce one shared `_invoke_maybe_awaitable(callback, *args)` helper and use it in Dispatcher, ACK/login handlers and Companion callback dispatch.

## Reproduction / verification

The deeper focused check passed a normal function returning a coroutine. `_invoke_callback()` created the coroutine but its body never ran.

## Triple verification

| Method | Result | Record |
|---|---|---|
| Static runtime trace | **Passed** | The complete reachable path and exact quoted source excerpts in this report were revalidated byte-for-byte against the supplied source trees. |
| Executable reproduction | **Passed** | `test_bug_025_confirmed_sync_wrapper_returned_awaitable_is_not_awaited` in [`REVERIFICATION-CHECKS.py`](../docs/REVERIFICATION-CHECKS.py). |
| Active falsification | **Passed** | The helper classifies the callable before invocation and never inspects the returned value for awaitability. See [`BASELINE-FALSIFICATION-CHECKS.py`](../docs/BASELINE-FALSIFICATION-CHECKS.py). |

The consolidated baseline matrix and captured results are in [`BASELINE-TRIPLE-VERIFICATION.md`](../docs/BASELINE-TRIPLE-VERIFICATION.md).

## Implementation plan

The former patch sketch has been replaced with a review-oriented plan covering the required repositories/files, implementation sequence, decisions to verify, regression tests, rollout and definition of done.

[Open `implementation_plan.md`](../implementation-plans/BUG-025/implementation_plan.md)


## Source references and excerpts

### Evidence 1: `src/openhop_core/node/dispatcher.py` lines 325–363

[Open source path](https://github.com/openhop-dev/openhop_core/blob/dev/src/openhop_core/node/dispatcher.py#L325-L363)

```text
  325 |         self, callback: Callable[[Packet], Awaitable[None] | None]
  326 |     ) -> None:
  327 |         self.packet_received_callback = callback
  328 | 
  329 |     def set_packet_sent_callback(
  330 |         self, callback: Callable[[Packet], Awaitable[None] | None]
  331 |     ) -> None:
  332 |         self.packet_sent_callback = callback
  333 | 
  334 |     def set_ack_received_listener(
  335 |         self,
  336 |         callback: Optional[Callable[[int], Awaitable[None] | None]],
  337 |     ) -> None:
  338 |         """Set optional listener for ACK CRCs (e.g. companion send_confirmed)."""
  339 |         self._ack_received_listener = callback
  340 | 
  341 |     def set_raw_packet_callback(
  342 |         self, callback: Callable[[Packet, bytes], Awaitable[None] | None]
  343 |     ) -> None:
  344 |         """Set callback for raw packet data (includes both parsed packet and raw bytes)."""
  345 |         self.raw_packet_callback = callback
  346 | 
  347 |     def add_raw_packet_subscriber(self, callback: Callable[..., Any]) -> None:
  348 |         """Subscribe to every raw packet. Callback (pkt, data) or (pkt, data, analysis).
  349 |         Forward raw RX to clients to track repeats by packet hash.
  350 |         """
  351 |         if callback not in self._raw_packet_subscribers:
  352 |             self._raw_packet_subscribers.append(callback)
  353 | 
  354 |     def remove_raw_packet_subscriber(self, callback: Callable[..., Any]) -> None:
  355 |         """Unsubscribe from raw packet notifications (after parse)."""
  356 |         try:
  357 |             self._raw_packet_subscribers.remove(callback)
  358 |         except ValueError:
  359 |             pass
  360 | 
  361 |     def add_raw_rx_subscriber(
  362 |         self, callback: Callable[[bytes, int, float], Awaitable[None] | None]
  363 |     ) -> None:
```

### Evidence 2: `src/openhop_core/node/dispatcher.py` lines 1082–1116

[Open source path](https://github.com/openhop-dev/openhop_core/blob/dev/src/openhop_core/node/dispatcher.py#L1082-L1116)

```text
 1082 |     async def _invoke_callback(self, cb, pkt: Packet) -> None:
 1083 |         if inspect.iscoroutinefunction(cb):
 1084 |             await cb(pkt)
 1085 |         else:
 1086 |             cb(pkt)
 1087 | 
 1088 |     async def _invoke_ack_listener(self, crc: int) -> None:
 1089 |         """Invoke ack-received listener (sync or async)."""
 1090 |         cb = self._ack_received_listener
 1091 |         if cb is None:
 1092 |             return
 1093 |         if inspect.iscoroutinefunction(cb):
 1094 |             await cb(crc)
 1095 |         else:
 1096 |             cb(crc)
 1097 | 
 1098 |     async def _invoke_enhanced_raw_callback(
 1099 |         self, callback, pkt: Packet, data: bytes, analysis: dict
 1100 |     ) -> None:
 1101 |         """Call raw packet callback with extra analysis data."""
 1102 |         try:
 1103 |             if inspect.iscoroutinefunction(callback):
 1104 |                 await callback(pkt, data, analysis)
 1105 |             else:
 1106 |                 callback(pkt, data, analysis)
 1107 |         except Exception as e:
 1108 |             self._log(f"Raw callback error: {e}")
 1109 |             # Fallback to original callback format
 1110 |             try:
 1111 |                 if inspect.iscoroutinefunction(callback):
 1112 |                     await callback(pkt, data)
 1113 |                 else:
 1114 |                     callback(pkt, data)
 1115 |             except Exception as e2:
 1116 |                 self._log(f"Fallback raw callback error: {e2}")
```

### Evidence 3: `src/openhop_core/node/dispatcher.py` lines 427–491

[Open source path](https://github.com/openhop-dev/openhop_core/blob/dev/src/openhop_core/node/dispatcher.py#L427-L491)

```text
  427 |     async def _process_received_packet(
  428 |         self,
  429 |         data: bytes,
  430 |         rssi: Optional[int] = None,
  431 |         snr: Optional[float] = None,
  432 |     ) -> None:
  433 |         """Process received packet. rssi/snr are per-packet when provided."""
  434 |         # Notify raw RX subscribers so clients can track repeats
  435 |         if rssi is not None:
  436 |             rssi_val = rssi
  437 |         elif hasattr(self.radio, "get_last_rssi"):
  438 |             rssi_val = self.radio.get_last_rssi()
  439 |         else:
  440 |             rssi_val = 0
  441 |         if snr is not None:
  442 |             snr_val = snr
  443 |         elif hasattr(self.radio, "get_last_snr"):
  444 |             snr_val = self.radio.get_last_snr()
  445 |         else:
  446 |             snr_val = 0.0
  447 |         for cb in self._raw_rx_subscribers:
  448 |             try:
  449 |                 if inspect.iscoroutinefunction(cb):
  450 |                     await cb(data, rssi_val, snr_val)
  451 |                 else:
  452 |                     cb(data, rssi_val, snr_val)
  453 |             except Exception as e:
  454 |                 self._log(f"Raw RX subscriber error: {e}")
  455 | 
  456 |         # Blacklist check uses raw-frame hash (catches known-bad bytes before parsing)
  457 |         raw_hash = self.packet_filter.generate_hash(data)
  458 |         if self.packet_filter.is_blacklisted(raw_hash):
  459 |             self._log("[RX DEBUG] Packet blacklisted, skipping")
  460 |             return
  461 | 
  462 |         # Parse before dedup — calculate_packet_hash() needs a parsed packet
  463 |         pkt = Packet()
  464 |         try:
  465 |             pkt.read_from(data)
  466 |         except Exception as err:
  467 |             self._log(f"Malformed packet: {err}")
  468 |             self.packet_filter.blacklist(raw_hash)
  469 |             self._log(f"Blacklisted malformed packet (raw hash: {raw_hash})")
  470 |             return
  471 | 
  472 |         # Use per-packet rssi/snr when provided (avoids race); else fall back to radio last values
  473 |         pkt._rssi = rssi if rssi is not None else self.radio.get_last_rssi()
  474 |         pkt._snr = snr if snr is not None else self.radio.get_last_snr()
  475 | 
  476 |         # Let the node know about this packet for analysis (statistics, caching, etc.)
  477 |         if self.packet_analysis_callback:
  478 |             try:
  479 |                 if inspect.iscoroutinefunction(self.packet_analysis_callback):
  480 |                     await self.packet_analysis_callback(pkt, data)
  481 |                 else:
  482 |                     self.packet_analysis_callback(pkt, data)
  483 |                 self._log("[RX DEBUG] Packet analysis callback completed")
  484 |             except Exception as e:
  485 |                 self._log(f"Error in packet analysis callback: {e}")
  486 | 
  487 |         # Notify raw packet subscribers (e.g. companion clients for PUSH_CODE_LOG_RX_DATA)
  488 |         # This fires BEFORE dedup so the UI sees all path variants for logging
  489 |         analysis = {}
  490 |         for callback in self._raw_packet_subscribers:
  491 |             await self._invoke_enhanced_raw_callback(callback, pkt, data, analysis)
```

### Evidence 4: `src/openhop_core/companion/base_callbacks.py` lines 44–50

[Open source path](https://github.com/openhop-dev/openhop_core/blob/dev/src/openhop_core/companion/base_callbacks.py#L44-L50)

```text
   44 |     @staticmethod
   45 |     async def _call_legacy(callback: Callable, *args: Any) -> None:
   46 |         """Invoke a legacy positional callback, awaiting it when async."""
   47 |         result = callback(*args)
   48 |         if inspect.isawaitable(result):
   49 |             await result
   50 | 
```

### Evidence 5: `src/openhop_core/companion/base_callbacks.py` lines 299–307

[Open source path](https://github.com/openhop-dev/openhop_core/blob/dev/src/openhop_core/companion/base_callbacks.py#L299-L307)

```text
  299 |     async def _fire_callbacks(self, event_name: str, *args: Any) -> None:
  300 |         for callback in self._push_callbacks.get(event_name, []):
  301 |             try:
  302 |                 if inspect.iscoroutinefunction(callback):
  303 |                     await callback(*args)
  304 |                 else:
  305 |                     callback(*args)
  306 |             except Exception as e:
  307 |                 logger.error("Error in %s callback: %s", event_name, e)
```
