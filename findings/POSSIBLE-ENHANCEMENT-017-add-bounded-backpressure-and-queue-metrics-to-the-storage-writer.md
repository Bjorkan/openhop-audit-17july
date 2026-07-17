# POSSIBLE-ENHANCEMENT-017 — Possible enhancement — add bounded backpressure and queue metrics to the storage writer

[← Audit index](../README.md)

| Field | Value |
|---|---|
| Classification | **Possible enhancement** |
| Severity | **Enhancement** |
| Confidence | **High** |
| Area | Storage reliability |
| Components | OpenHop Repeater |
| Audit date | 2026-07-17 |
| Status | Open in supplied snapshot |

## TL;DR

The single-thread executor preserves ordering but its work queue is unbounded and submissions are fire-and-forget.

## What happens now

If SQLite aggregation or network publication remains slower than packet arrival, pending tasks can grow without a visible bound or operator metric.

## Expected behaviour / proposed direction

Use a bounded queue with explicit drop/coalescing policy and expose pending depth, oldest age and rejected count.

## What needs to change

Turns overload into controlled, observable behavior instead of latent memory growth.

## Suggested code change

> **Review warning:** the linked patch is an LLM-generated implementation sketch. It is intended to show the approximate change surface, not to be applied blindly. Rebase it onto the current source, add regression tests, and review concurrency, persistence and protocol implications.

[Open the suggested patch](../patches/POSSIBLE-ENHANCEMENT-017.patch)

## Source references and excerpts

### Evidence 1: `repeater/data_acquisition/storage_collector.py` lines 180–240

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
