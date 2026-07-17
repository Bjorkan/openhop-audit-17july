# BUG-025 — Callbacks returning awaitables from synchronous wrappers are silently not awaited

[← Audit index](../README.md)

| Field | Value |
|---|---|
| Classification | **Confirmed defect** |
| Severity | **Medium** |
| Confidence | **Confirmed** |
| Area | Callback dispatch / async interoperability |
| Components | OpenHop Core |
| Audit date | 2026-07-17 |
| Status | Open in supplied snapshot |

## TL;DR

Multiple callback helpers decide whether to await by checking `inspect.iscoroutinefunction(callback)`. A normal callable that returns an awaitable is called but its coroutine is discarded.

## What happens now

This affects callable objects with async `__call__`, decorated async functions whose wrapper is synchronous, partial/proxy functions and intentionally synchronous adapters returning a coroutine. Type annotations allow `Awaitable | None`, and another helper in the same module already implements the correct “call, then inspect result” pattern.

## Expected behaviour / proposed direction

Callback invocation should always call once, inspect the returned object and await it when `inspect.isawaitable(result)` is true.

## What needs to change

Introduce one shared `_invoke_maybe_awaitable(callback, *args)` helper and use it in Dispatcher, ACK/login handlers and Companion callback dispatch.

## Reproduction / verification

The deeper focused check passed a normal function returning a coroutine. `_invoke_callback()` created the coroutine but its body never ran.

## Suggested code change

> **Review warning:** the linked patch is an LLM-generated implementation sketch. It is intended to show the approximate change surface, not to be applied blindly. Rebase it onto the current source, add regression tests, and review concurrency, persistence and protocol implications.

[Open the suggested patch](../patches/BUG-025.patch)

## Source references and excerpts

### Evidence 1: `src/openhop_core/node/dispatcher.py` lines 295–333

[Open source path](https://github.com/openhop-dev/openhop_core/blob/dev/src/openhop_core/node/dispatcher.py#L295-L333)

```text
  295 |         self, callback: Callable[[Packet], Awaitable[None] | None]
  296 |     ) -> None:
  297 |         self.packet_received_callback = callback
  298 | 
  299 |     def set_packet_sent_callback(
  300 |         self, callback: Callable[[Packet], Awaitable[None] | None]
  301 |     ) -> None:
  302 |         self.packet_sent_callback = callback
  303 | 
  304 |     def set_ack_received_listener(
  305 |         self,
  306 |         callback: Optional[Callable[[int], Awaitable[None] | None]],
  307 |     ) -> None:
  308 |         """Set optional listener for ACK CRCs (e.g. companion send_confirmed)."""
  309 |         self._ack_received_listener = callback
  310 | 
  311 |     def set_raw_packet_callback(
  312 |         self, callback: Callable[[Packet, bytes], Awaitable[None] | None]
  313 |     ) -> None:
  314 |         """Set callback for raw packet data (includes both parsed packet and raw bytes)."""
  315 |         self.raw_packet_callback = callback
  316 | 
  317 |     def add_raw_packet_subscriber(self, callback: Callable[..., Any]) -> None:
  318 |         """Subscribe to every raw packet. Callback (pkt, data) or (pkt, data, analysis).
  319 |         Forward raw RX to clients to track repeats by packet hash.
  320 |         """
  321 |         if callback not in self._raw_packet_subscribers:
  322 |             self._raw_packet_subscribers.append(callback)
  323 | 
  324 |     def remove_raw_packet_subscriber(self, callback: Callable[..., Any]) -> None:
  325 |         """Unsubscribe from raw packet notifications (after parse)."""
  326 |         try:
  327 |             self._raw_packet_subscribers.remove(callback)
  328 |         except ValueError:
  329 |             pass
  330 | 
  331 |     def add_raw_rx_subscriber(
  332 |         self, callback: Callable[[bytes, int, float], Awaitable[None] | None]
  333 |     ) -> None:
```

### Evidence 2: `src/openhop_core/node/dispatcher.py` lines 772–806

[Open source path](https://github.com/openhop-dev/openhop_core/blob/dev/src/openhop_core/node/dispatcher.py#L772-L806)

```text
  772 |     async def _invoke_callback(self, cb, pkt: Packet) -> None:
  773 |         if inspect.iscoroutinefunction(cb):
  774 |             await cb(pkt)
  775 |         else:
  776 |             cb(pkt)
  777 | 
  778 |     async def _invoke_ack_listener(self, crc: int) -> None:
  779 |         """Invoke ack-received listener (sync or async)."""
  780 |         cb = self._ack_received_listener
  781 |         if cb is None:
  782 |             return
  783 |         if inspect.iscoroutinefunction(cb):
  784 |             await cb(crc)
  785 |         else:
  786 |             cb(crc)
  787 | 
  788 |     async def _invoke_enhanced_raw_callback(
  789 |         self, callback, pkt: Packet, data: bytes, analysis: dict
  790 |     ) -> None:
  791 |         """Call raw packet callback with extra analysis data."""
  792 |         try:
  793 |             if inspect.iscoroutinefunction(callback):
  794 |                 await callback(pkt, data, analysis)
  795 |             else:
  796 |                 callback(pkt, data, analysis)
  797 |         except Exception as e:
  798 |             self._log(f"Raw callback error: {e}")
  799 |             # Fallback to original callback format
  800 |             try:
  801 |                 if inspect.iscoroutinefunction(callback):
  802 |                     await callback(pkt, data)
  803 |                 else:
  804 |                     callback(pkt, data)
  805 |             except Exception as e2:
  806 |                 self._log(f"Fallback raw callback error: {e2}")
```

### Evidence 3: `src/openhop_core/node/dispatcher.py` lines 397–461

[Open source path](https://github.com/openhop-dev/openhop_core/blob/dev/src/openhop_core/node/dispatcher.py#L397-L461)

```text
  397 |     async def _process_received_packet(
  398 |         self,
  399 |         data: bytes,
  400 |         rssi: Optional[int] = None,
  401 |         snr: Optional[float] = None,
  402 |     ) -> None:
  403 |         """Process received packet. rssi/snr are per-packet when provided."""
  404 |         # Notify raw RX subscribers so clients can track repeats
  405 |         if rssi is not None:
  406 |             rssi_val = rssi
  407 |         elif hasattr(self.radio, "get_last_rssi"):
  408 |             rssi_val = self.radio.get_last_rssi()
  409 |         else:
  410 |             rssi_val = 0
  411 |         if snr is not None:
  412 |             snr_val = snr
  413 |         elif hasattr(self.radio, "get_last_snr"):
  414 |             snr_val = self.radio.get_last_snr()
  415 |         else:
  416 |             snr_val = 0.0
  417 |         for cb in self._raw_rx_subscribers:
  418 |             try:
  419 |                 if inspect.iscoroutinefunction(cb):
  420 |                     await cb(data, rssi_val, snr_val)
  421 |                 else:
  422 |                     cb(data, rssi_val, snr_val)
  423 |             except Exception as e:
  424 |                 self._log(f"Raw RX subscriber error: {e}")
  425 | 
  426 |         # Blacklist check uses raw-frame hash (catches known-bad bytes before parsing)
  427 |         raw_hash = self.packet_filter.generate_hash(data)
  428 |         if self.packet_filter.is_blacklisted(raw_hash):
  429 |             self._log("[RX DEBUG] Packet blacklisted, skipping")
  430 |             return
  431 | 
  432 |         # Parse before dedup — calculate_packet_hash() needs a parsed packet
  433 |         pkt = Packet()
  434 |         try:
  435 |             pkt.read_from(data)
  436 |         except Exception as err:
  437 |             self._log(f"Malformed packet: {err}")
  438 |             self.packet_filter.blacklist(raw_hash)
  439 |             self._log(f"Blacklisted malformed packet (raw hash: {raw_hash})")
  440 |             return
  441 | 
  442 |         # Use per-packet rssi/snr when provided (avoids race); else fall back to radio last values
  443 |         pkt._rssi = rssi if rssi is not None else self.radio.get_last_rssi()
  444 |         pkt._snr = snr if snr is not None else self.radio.get_last_snr()
  445 | 
  446 |         # Let the node know about this packet for analysis (statistics, caching, etc.)
  447 |         if self.packet_analysis_callback:
  448 |             try:
  449 |                 if inspect.iscoroutinefunction(self.packet_analysis_callback):
  450 |                     await self.packet_analysis_callback(pkt, data)
  451 |                 else:
  452 |                     self.packet_analysis_callback(pkt, data)
  453 |                 self._log("[RX DEBUG] Packet analysis callback completed")
  454 |             except Exception as e:
  455 |                 self._log(f"Error in packet analysis callback: {e}")
  456 | 
  457 |         # Notify raw packet subscribers (e.g. companion clients for PUSH_CODE_LOG_RX_DATA)
  458 |         # This fires BEFORE dedup so the UI sees all path variants for logging
  459 |         analysis = {}
  460 |         for callback in self._raw_packet_subscribers:
  461 |             await self._invoke_enhanced_raw_callback(callback, pkt, data, analysis)
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
