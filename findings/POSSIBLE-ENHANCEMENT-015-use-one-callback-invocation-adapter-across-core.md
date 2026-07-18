# POSSIBLE-ENHANCEMENT-015 — Possible enhancement — use one callback invocation adapter across Core

[← Audit index](../README.md)

> Reverification verdict: **Factual premise confirmed; implementation remains optional.**

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

### Evidence 1: `src/openhop_core/node/dispatcher.py` lines 1082–1116

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

### Evidence 2: `src/openhop_core/node/dispatcher.py` lines 427–491

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
