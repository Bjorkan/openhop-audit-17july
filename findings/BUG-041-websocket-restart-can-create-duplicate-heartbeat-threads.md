# BUG-041 — WebSocket restart can leave duplicate heartbeat threads running

[← Audit index](../README.md)

> Triple-verification verdict: **confirmed against the supplied snapshots**. This report was included only after three independent checks passed.

| Field | Value |
|---|---|
| Classification | **Confirmed defect** |
| Severity | 🟠 **Medium** |
| Confidence | **Triple-verified** |
| Area | WebSocket lifecycle |
| Components | OpenHop Repeater |
| Audit date | 2026-07-17 |

## TL;DR

Shutdown clears a shared boolean and drops the thread reference without joining. If startup sets the same boolean true before the sleeping old loop rechecks it, both old and new threads continue and send heartbeats to the same client set.

## Expected behavior

At most one heartbeat worker may exist for a server generation, and shutdown must wait for or permanently invalidate the old worker.

## Required direction

1. Use a per-worker `Event`/generation token rather than one restartable module boolean.
2. Join the old thread outside locks before discarding its reference.
3. Make start/stop serialized and idempotent.

## Triple verification

| Method | Check | Result | Observation |
|---|---|---|---|
| Static runtime trace | Heartbeat start/stop ownership | **Passed** | Shutdown drops the thread reference without joining, while old and new loops share one boolean run flag. |
| Executable reproduction | Immediate restart | **Passed** | The old heartbeat thread is alive when the new thread starts, and both remain alive. |
| Active falsification | Externally visible effect | **Passed** | Both workers send pings to the same client collection, excluding a harmless stale-thread interpretation. |

The executable checks are preserved under [`docs/triple-verification/`](../docs/triple-verification/) and were rerun from clean Python processes for this edition. The third row is an explicit falsification/countercheck that searches for a guard, alternate adapter, normalization, documented contract or unreachable-state explanation that would invalidate the finding.

## Implementation plan

See [`implementation-plans/BUG-041/implementation_plan.md`](../implementation-plans/BUG-041/implementation_plan.md).

## Source evidence

### Evidence 1: `repeater/data_acquisition/websocket_handler.py` lines 150–185

[Open source path](https://github.com/openhop-dev/openhop_repeater/blob/dev/repeater/data_acquisition/websocket_handler.py#L150-L185)

```text
  150 | def _heartbeat_loop():
  151 |     """Background thread to send periodic pings to all connected clients"""
  152 |     global _heartbeat_running
  153 | 
  154 |     while _heartbeat_running:
  155 |         time.sleep(PING_INTERVAL)
  156 | 
  157 |         if not _connected_clients:
  158 |             continue
  159 | 
  160 |         ping_message = json.dumps({"type": "ping"})
  161 | 
  162 |         for client in list(_connected_clients):
  163 |             try:
  164 |                 client.send(ping_message)
  165 |             except Exception as e:
  166 |                 logger.debug(f"Heartbeat ping failed: {e}")
  167 |                 _connected_clients.discard(client)
  168 | 
  169 | 
  170 | def init_websocket():
  171 |     """Initialize WebSocket plugin and start heartbeat"""
  172 |     global _heartbeat_thread, _heartbeat_running, _websocket_plugin
  173 | 
  174 |     # Re-initialize plugin safely across CherryPy stop/start cycles.
  175 |     # ws4py's manager thread cannot be started twice, so always tear down
  176 |     # any previously subscribed plugin instance before creating a new one.
  177 |     if _websocket_plugin is not None:
  178 |         try:
  179 |             _websocket_plugin.unsubscribe()
  180 |         except Exception as e:
  181 |             logger.debug(f"WebSocket plugin unsubscribe during init failed: {e}")
  182 |         _websocket_plugin = None
  183 | 
  184 |     _websocket_plugin = WebSocketPlugin(cherrypy.engine)
  185 |     _websocket_plugin.subscribe()
```
### Evidence 2: `repeater/data_acquisition/websocket_handler.py` lines 198–211

[Open source path](https://github.com/openhop-dev/openhop_repeater/blob/dev/repeater/data_acquisition/websocket_handler.py#L198-L211)

```text
  198 | def shutdown_websocket():
  199 |     """Stop websocket heartbeat and unsubscribe plugin for clean restart."""
  200 |     global _heartbeat_running, _heartbeat_thread, _websocket_plugin
  201 | 
  202 |     _heartbeat_running = False
  203 |     _heartbeat_thread = None
  204 |     _connected_clients.clear()
  205 | 
  206 |     if _websocket_plugin is not None:
  207 |         try:
  208 |             _websocket_plugin.unsubscribe()
  209 |         except Exception as e:
  210 |             logger.debug(f"WebSocket plugin unsubscribe failed: {e}")
  211 |         _websocket_plugin = None
```

