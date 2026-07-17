# POSSIBLE-ENHANCEMENT-015 — Possible enhancement — use one callback invocation adapter across Core

[← Audit index](../README.md)

| Field | Value |
|---|---|
| Classification | **Possible enhancement** |
| Severity | **Enhancement** |
| Confidence | **High** |
| Area | Async callback code reuse |
| Components | OpenHop Core |
| Audit date | 2026-07-17 |
| Status | Open in supplied snapshot |

## TL;DR

Dispatcher, handlers and Companion implement several slightly different sync/async callback dispatch patterns.

## What happens now

Some inspect the function object, one correctly inspects the returned value, and enhanced raw callbacks also implement an exception-based signature fallback.

## Expected behaviour / proposed direction

One adapter should select a supported signature before invocation, invoke once, await returned awaitables and apply a consistent error policy.

## What needs to change

Eliminates repeated branches, fixes decorated/callable-object behavior and centralizes callback observability.

## Implementation plan

The former patch sketch has been replaced with a review-oriented plan covering the required repositories/files, implementation sequence, decisions to verify, regression tests, rollout and definition of done.

[Open `implementation_plan.md`](../implementation-plans/POSSIBLE-ENHANCEMENT-015/implementation_plan.md)


## Source references and excerpts

### Evidence 1: `src/openhop_core/node/dispatcher.py` lines 772–806

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

### Evidence 2: `src/openhop_core/node/dispatcher.py` lines 397–461

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

### Evidence 3: `src/openhop_core/companion/base_callbacks.py` lines 44–50

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

### Evidence 4: `src/openhop_core/companion/base_callbacks.py` lines 299–307

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
