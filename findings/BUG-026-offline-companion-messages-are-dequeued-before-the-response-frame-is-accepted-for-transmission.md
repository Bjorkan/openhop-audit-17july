# BUG-026 — Offline companion messages are dequeued before the response frame is accepted for transmission

[← Audit index](../README.md)

| Field | Value |
|---|---|
| Classification | **Confirmed defect** |
| Severity | **High** |
| Confidence | **Confirmed** |
| Area | Companion offline queue / delivery reliability |
| Components | OpenHop Core + OpenHop Repeater |
| Audit date | 2026-07-17 |
| Status | Open in supplied snapshot |

## TL;DR

`sync_next_message()` destructively pops the message before `_write_frame()`. The transport can then silently drop the frame because there is no client queue, the payload is oversized or the queue is full.

## What happens now

The command returns no delivery acknowledgment from `_enqueue_frame()`. Once the queue pop or SQLite pop has occurred, a failed enqueue loses the only copy even though the companion never received it.

## Expected behaviour / proposed direction

Offline messages should be removed only after the outbound frame has been accepted, and ideally after transport acknowledgment or connection completion.

## What needs to change

Use peek/reserve/commit semantics. Make `_enqueue_frame()` return success, enqueue first, then commit deletion of the reserved in-memory or persisted row.

## Reproduction / verification

The deeper focused check filled the outbound queue, then requested the next offline message. The frame was dropped as `QueueFull` and the offline queue became empty.

## Implementation plan

The former patch sketch has been replaced with a review-oriented plan covering the required repositories/files, implementation sequence, decisions to verify, regression tests, rollout and definition of done.

[Open `implementation_plan.md`](../implementation-plans/BUG-026/implementation_plan.md)


## Source references and excerpts

### Evidence 1: `src/openhop_core/companion/frame_server/commands_messaging.py` lines 430–437

[Open source path](https://github.com/openhop-dev/openhop_core/blob/dev/src/openhop_core/companion/frame_server/commands_messaging.py#L430-L437)

```text
  430 |     async def _cmd_sync_next_message(self, data: bytes) -> None:
  431 |         msg = self.bridge.sync_next_message()
  432 |         if msg is None:
  433 |             msg = await asyncio.to_thread(self._sync_next_from_persistence)
  434 |         if msg is None:
  435 |             self._write_frame(bytes([RESP_CODE_NO_MORE_MESSAGES]))
  436 |             return
  437 |         self._write_frame(self._build_message_frame(msg))
```

### Evidence 2: `repeater/companion/frame_server.py` lines 130–138

[Open source path](https://github.com/openhop-dev/openhop_repeater/blob/dev/repeater/companion/frame_server.py#L130-L138)

```text
  130 |     async def _cmd_sync_next_message(self, data: bytes) -> None:
  131 |         """Sync next message; run persistence read in thread so SQLite does not block."""
  132 |         msg = self.bridge.sync_next_message()
  133 |         if msg is None:
  134 |             msg = await asyncio.to_thread(self._sync_next_from_persistence)
  135 |         if msg is None:
  136 |             self._write_frame(bytes([RESP_CODE_NO_MORE_MESSAGES]))
  137 |             return
  138 |         self._write_frame(self._build_message_frame(msg))
```

### Evidence 3: `src/openhop_core/companion/frame_server/transport.py` lines 88–113

[Open source path](https://github.com/openhop-dev/openhop_core/blob/dev/src/openhop_core/companion/frame_server/transport.py#L88-L113)

```text
   88 |     def _enqueue_frame(self, data: bytes) -> None:
   89 |         """Build an outbound frame and enqueue it for the writer task.
   90 | 
   91 |         Sync, non-blocking.  On ``QueueFull`` the frame is dropped with a
   92 |         warning — this provides natural backpressure shedding.
   93 |         """
   94 |         if self._write_queue is None:
   95 |             return
   96 |         if len(data) > MAX_PAYLOAD_SIZE:
   97 |             # Firmware writeFrame() refuses (returns 0) rather than truncating; a
   98 |             # truncated frame would corrupt the response. Drop it instead.
   99 |             logger.warning(
  100 |                 "Outbound frame payload too large (%s > %s); dropping frame",
  101 |                 len(data),
  102 |                 MAX_PAYLOAD_SIZE,
  103 |             )
  104 |             return
  105 |         frame = bytes([FRAME_OUTBOUND_PREFIX]) + struct.pack("<H", len(data)) + data
  106 |         try:
  107 |             self._write_queue.put_nowait(frame)
  108 |         except asyncio.QueueFull:
  109 |             logger.warning("Write queue full (%s); dropping frame", self._write_queue.maxsize)
  110 | 
  111 |     def _write_frame(self, data: bytes) -> None:
  112 |         """Alias for ``_enqueue_frame``; retained for subclass compatibility."""
  113 |         self._enqueue_frame(data)
```
