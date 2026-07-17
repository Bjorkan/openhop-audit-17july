# POSSIBLE-ENHANCEMENT-018 — Possible enhancement — use an acknowledged outbox for companion offline delivery

[← Audit index](../README.md)

> Reverification verdict: **Factual premise confirmed; implementation remains optional.**

| Field | Value |
|---|---|
| Classification | **Possible enhancement** |
| Severity | **Enhancement** |
| Confidence | **High** |
| Area | Companion reliability architecture |
| Components | OpenHop Core + OpenHop Repeater |
| Audit date | 2026-07-17 |
| Status | Open in supplied snapshot |

## TL;DR

Message ownership is split between an in-memory FIFO, SQLite rows and a non-acknowledging transport queue. Destructive pop and queue-full shedding are documented current semantics, but stable identities and reserve/commit states would support a stronger delivery guarantee.

## What happens now

Moves between layers are expressed as destructive pop operations. This matches the documented “pop next queued message” and transport-shedding behavior, but makes queue-full, disconnect, retry and concurrency outcomes difficult to reason about.

## Expected behaviour / proposed direction

Use one outbox abstraction with stable message IDs and states such as queued, reserved, enqueued and acknowledged.

## What needs to change

Provides at-least-once or exactly-once semantics by design and makes restart recovery deterministic.

## Implementation plan

The former patch sketch has been replaced with a review-oriented plan covering the required repositories/files, implementation sequence, decisions to verify, regression tests, rollout and definition of done.

[Open `implementation_plan.md`](../implementation-plans/POSSIBLE-ENHANCEMENT-018/implementation_plan.md)


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

### Evidence 2: `src/openhop_core/companion/frame_server/transport.py` lines 88–113

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

### Evidence 3: `repeater/companion/frame_server.py` lines 69–99

[Open source path](https://github.com/openhop-dev/openhop_repeater/blob/dev/repeater/companion/frame_server.py#L69-L99)

```text
   69 |     async def _persist_companion_message(self, msg_dict: dict) -> None:
   70 |         """Persist message to SQLite and pop from bridge queue.
   71 | 
   72 |         The bridge's ``offline_queue_size`` (``message_queue.max_size``) doubles
   73 |         as the SQLite retention limit: 0 disables offline storage entirely, so the
   74 |         message is dropped instead of persisted.
   75 |         """
   76 |         if not self.sqlite_handler:
   77 |             return
   78 |         # Older cores predate the public max_size property.
   79 |         retention = getattr(
   80 |             self.bridge.message_queue,
   81 |             "max_size",
   82 |             getattr(self.bridge.message_queue, "_max_size", None),
   83 |         )
   84 |         if retention == 0:
   85 |             self.bridge.message_queue.pop_last()
   86 |             return
   87 |         persisted = await asyncio.to_thread(
   88 |             self.sqlite_handler.companion_push_message,
   89 |             self.companion_hash,
   90 |             msg_dict,
   91 |             retention,
   92 |         )
   93 |         if persisted:
   94 |             self.bridge.message_queue.pop_last()
   95 |         else:
   96 |             logger.debug(
   97 |                 "Companion %s: retaining message in memory after SQLite queue rejection",
   98 |                 self.companion_hash,
   99 |             )
```

### Evidence 4: `src/openhop_core/companion/message_queue.py` lines 32–61

[Open source path](https://github.com/openhop-dev/openhop_core/blob/dev/src/openhop_core/companion/message_queue.py#L32-L61)

```text
   32 |     def push(self, msg: QueuedMessage) -> bool:
   33 |         """Add a message to the queue using MeshCore's protected eviction rule.
   34 | 
   35 |         At capacity, remove the oldest channel message and append ``msg``. If
   36 |         every retained message is direct, retain them all and reject ``msg``.
   37 |         Returns whether ``msg`` was queued.
   38 |         """
   39 |         if self._max_size <= 0:
   40 |             return False
   41 |         if len(self._queue) >= self._max_size:
   42 |             for index, queued in enumerate(self._queue):
   43 |                 if queued.is_channel:
   44 |                     del self._queue[index]
   45 |                     break
   46 |             else:
   47 |                 return False
   48 |         self._queue.append(msg)
   49 |         return True
   50 | 
   51 |     def pop(self) -> Optional[QueuedMessage]:
   52 |         """Remove and return the oldest message, or None if empty."""
   53 |         if self._queue:
   54 |             return self._queue.popleft()
   55 |         return None
   56 | 
   57 |     def pop_last(self) -> Optional[QueuedMessage]:
   58 |         """Remove and return the most recently pushed message, or None if empty."""
   59 |         if self._queue:
   60 |             return self._queue.pop()
   61 |         return None
```
