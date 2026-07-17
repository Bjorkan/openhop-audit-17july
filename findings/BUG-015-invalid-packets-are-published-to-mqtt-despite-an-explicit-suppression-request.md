# BUG-015 — Invalid packets are published to MQTT despite an explicit suppression request

[← Audit index](../README.md)

> Reverification verdict: **Confirmed against the supplied snapshot.**

| Field | Value |
|---|---|
| Classification | **Confirmed defect** |
| Severity | **Medium** |
| Confidence | **Confirmed** |
| Area | Packet publication / external telemetry |
| Components | OpenHop Repeater |
| Audit date | 2026-07-17 |
| Status | Open in supplied snapshot |

## TL;DR

The engine explicitly asks storage not to publish malformed packets to MQTT, but `StorageCollector` forwards the flag through two methods and then ignores it.

## What happens now

`record_packet()` documents `skip_mqtt_if_invalid`; `_record_packet_blocking()` passes it to `_publish_packet_sync()`. That method always invokes `_publish_packet_to_mqtt()` regardless of the value. Invalid adverts, empty payloads and overlong paths therefore leak to external MQTT consumers.

## Expected behaviour / proposed direction

Storage and local diagnostics may retain invalid packets, but the caller-selected external publication policy must be honored.

## What needs to change

Guard only the MQTT call with `if not skip_mqtt`. Keep Glass/WebSocket behavior explicit rather than overloading the same boolean for every sink.

## Reproduction / verification

The deeper focused check called `_publish_packet_sync(..., skip_mqtt=True)` and observed one MQTT publication call.

## Implementation plan

The former patch sketch has been replaced with a review-oriented plan covering the required repositories/files, implementation sequence, decisions to verify, regression tests, rollout and definition of done.

[Open `implementation_plan.md`](../implementation-plans/BUG-015/implementation_plan.md)


## Source references and excerpts

### Evidence 1: `repeater/engine.py` lines 553–576

[Open source path](https://github.com/openhop-dev/openhop_repeater/blob/dev/repeater/engine.py#L553-L576)

```text
  553 |         # Store packet record to persistent storage
  554 |         # Skip mqtt only for invalid packets (not duplicates or operational drops)
  555 |         if self.storage:
  556 |             try:
  557 |                 # Only skip mqtt for actual invalid/bad packets
  558 |                 invalid_reasons = (
  559 |                     DropReason.INVALID_ADVERT,
  560 |                     DropReason.EMPTY_PAYLOAD,
  561 |                     DropReason.PATH_TOO_LONG,
  562 |                 )
  563 |                 skip_mqtt = drop_reason in invalid_reasons if drop_reason else False
  564 |                 self.storage.record_packet(packet_record, skip_mqtt_if_invalid=skip_mqtt)
  565 |             except Exception as e:
  566 |                 logger.error(f"Failed to store packet record: {e}")
  567 | 
  568 |         # If this is a duplicate, try to attach it to the original packet
  569 |         if is_dupe and len(self.recent_packets) > 0:
  570 |             prev_pkt = self._recent_hash_index.get(packet_record["packet_hash"])
  571 |             if prev_pkt is not None:
  572 |                 # Add duplicate to original packet's duplicate list
  573 |                 if "duplicates" not in prev_pkt:
  574 |                     prev_pkt["duplicates"] = []
  575 |                 if len(prev_pkt["duplicates"]) < self.max_duplicates_per_packet:
  576 |                     prev_pkt["duplicates"].append(packet_record)
```

### Evidence 2: `repeater/data_acquisition/storage_collector.py` lines 180–240

[Open source path](https://github.com/openhop-dev/openhop_repeater/blob/dev/repeater/data_acquisition/storage_collector.py#L180-L240)

```text
  180 |     def record_packet(self, packet_record: dict, skip_mqtt_if_invalid: bool = True):
  181 |         """Record a packet to storage and publish it.
  182 | 
  183 |         All blocking work — the SQLite write, the cumulative-counts aggregate, the
  184 |         RRD update, and network publishing — runs on the dedicated writer thread so
  185 |         it never blocks the asyncio event loop. Callers treat this as
  186 |         fire-and-forget (the previous synchronous version blocked the loop).
  187 | 
  188 |         Args:
  189 |             packet_record: Dictionary containing packet information
  190 |             skip_mqtt_if_invalid: If True, don't publish packets with drop_reason to mqtt
  191 |         """
  192 |         logger.debug(
  193 |             f"Recording packet: type={packet_record.get('type')}, "
  194 |             f"transmitted={packet_record.get('transmitted')}"
  195 |         )
  196 |         self._submit_db(self._record_packet_blocking, packet_record, skip_mqtt_if_invalid)
  197 | 
  198 |     def _submit_db(self, fn, *args):
  199 |         """Run a blocking storage operation on the dedicated writer thread.
  200 | 
  201 |         Falls back to running inline only if the executor has already been shut
  202 |         down (process teardown), so late records are not silently dropped.
  203 |         """
  204 |         try:
  205 |             self._db_executor.submit(self._run_db_task, fn, *args)
  206 |         except RuntimeError:
  207 |             self._run_db_task(fn, *args)
  208 | 
  209 |     def _run_db_task(self, fn, *args):
  210 |         """Execute a writer-thread task, logging (not raising) on failure."""
  211 |         try:
  212 |             fn(*args)
  213 |         except Exception as e:
  214 |             logger.error(f"Storage writer task failed: {e}", exc_info=True)
  215 | 
  216 |     def _record_packet_blocking(self, packet_record: dict, skip_mqtt: bool):
  217 |         """Store, aggregate, update metrics, and publish one packet (writer thread)."""
  218 |         packet_id = self.sqlite_handler.store_packet(packet_record)
  219 |         if packet_id is not None:
  220 |             packet_record["id"] = packet_id
  221 |         cumulative_counts = self.sqlite_handler.get_cumulative_counts()
  222 |         self.rrd_handler.update_packet_metrics(packet_record, cumulative_counts)
  223 |         self._publish_packet_sync(packet_record, skip_mqtt)
  224 | 
  225 |     def _publish_packet_sync(self, packet_record: dict, skip_mqtt: bool):
  226 |         """Publish a single packet (glass, per-packet WebSocket event, MQTT).
  227 | 
  228 |         Only fast, per-packet work runs here. The aggregate stats broadcast is
  229 |         driven separately by _stats_broadcast_loop so the writer thread is not
  230 |         held by the multi-second get_packet_stats(24h) query.
  231 |         """
  232 |         self._publish_to_glass(packet_record, "packet")
  233 | 
  234 |         if self.websocket_available:
  235 |             try:
  236 |                 self.websocket_broadcast_packet(packet_record)
  237 |             except Exception as e:
  238 |                 logger.debug(f"WebSocket broadcast failed: {e}")
  239 | 
  240 |         self._publish_packet_to_mqtt(packet_record)
```
