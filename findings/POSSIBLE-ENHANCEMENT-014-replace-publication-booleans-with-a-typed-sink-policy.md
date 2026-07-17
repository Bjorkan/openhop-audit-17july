# POSSIBLE-ENHANCEMENT-014 — Possible enhancement — replace publication booleans with a typed sink policy

[← Audit index](../README.md)

| Field | Value |
|---|---|
| Classification | **Possible enhancement** |
| Severity | **Enhancement** |
| Confidence | **High** |
| Area | Telemetry architecture |
| Components | OpenHop Repeater |
| Audit date | 2026-07-17 |
| Status | Open in supplied snapshot |

## TL;DR

`skip_mqtt_if_invalid` is threaded through storage methods while Glass and WebSocket publication remain implicit.

## What happens now

A negative boolean with conditional semantics is easy to ignore and does not explain whether invalid records should reach each individual sink.

## Expected behaviour / proposed direction

Pass a typed publication policy such as `PublicationTargets(storage=True, glass=True, websocket=True, mqtt=False)`.

## What needs to change

Makes each sink decision explicit, avoids inverted flags and simplifies tests for invalid, duplicate and operational-drop records.

## Suggested code change

> **Review warning:** the linked patch is an LLM-generated implementation sketch. It is intended to show the approximate change surface, not to be applied blindly. Rebase it onto the current source, add regression tests, and review concurrency, persistence and protocol implications.

[Open the suggested patch](../patches/POSSIBLE-ENHANCEMENT-014.patch)

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
