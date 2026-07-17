# BUG-027 — Concurrent message persistence can remove a different, newer message from memory

[← Audit index](../README.md)

> Reverification verdict: **Confirmed against the supplied snapshot.**

| Field | Value |
|---|---|
| Classification | **Confirmed defect** |
| Severity | **High** |
| Confidence | **Confirmed** |
| Area | Companion persistence / concurrency |
| Components | OpenHop Core + OpenHop Repeater |
| Audit date | 2026-07-17 |
| Status | Open in supplied snapshot |

## TL;DR

After awaiting SQLite insertion, the repeater removes “the most recently pushed message” rather than the specific message that was persisted.

## What happens now

While `_persist_companion_message()` awaits `asyncio.to_thread()`, another packet task can push a newer message. On success, `pop_last()` removes that newer message. The older persisted message remains in memory, causing a duplicate later, while the newer unpersisted message is lost.

## Expected behaviour / proposed direction

Persistence completion must remove the exact queue entry associated with that operation, independent of interleaving pushes.

## What needs to change

Assign queue entry IDs/tokens and remove by identity after successful persistence. Better, make the queue/persistence layer one transactional outbox with serialized ownership.

## Reproduction / verification

The deeper focused check inserted a second message during the awaited SQLite call. `pop_last()` removed the second message and left the first, already-persisted message in memory.

## Implementation plan

The former patch sketch has been replaced with a review-oriented plan covering the required repositories/files, implementation sequence, decisions to verify, regression tests, rollout and definition of done.

[Open `implementation_plan.md`](../implementation-plans/BUG-027/implementation_plan.md)


## Source references and excerpts

### Evidence 1: `repeater/companion/frame_server.py` lines 69–99

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

### Evidence 2: `src/openhop_core/companion/message_queue.py` lines 32–61

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

### Evidence 3: `src/openhop_core/companion/frame_server/push.py` lines 58–110

[Open source path](https://github.com/openhop-dev/openhop_core/blob/dev/src/openhop_core/companion/frame_server/push.py#L58-L110)

```text
   58 |     async def _on_message_event(self, event: MessageEvent):
   59 |         msg_dict = {
   60 |             "sender_key": event.sender_key,
   61 |             "text": event.text,
   62 |             "timestamp": event.timestamp,
   63 |             "txt_type": event.txt_type,
   64 |             "is_channel": False,
   65 |             "channel_idx": 0,
   66 |             "path_len": event.path_len,
   67 |             "packet_hash": event.packet_hash,
   68 |             "snr": event.snr,
   69 |             "rssi": event.rssi,
   70 |             "sender_prefix": event.sender_prefix,
   71 |         }
   72 |         if event.queued:
   73 |             await self._persist_companion_message(msg_dict)
   74 |         self._enqueue_frame(bytes([PUSH_CODE_MSG_WAITING]))
   75 | 
   76 |     async def _on_channel_message_event(self, event: ChannelMessageEvent):
   77 |         msg_dict = {
   78 |             "sender_key": b"",
   79 |             "text": event.text,
   80 |             "timestamp": event.timestamp,
   81 |             "txt_type": 0,
   82 |             "is_channel": True,
   83 |             "channel_idx": event.channel_idx,
   84 |             "path_len": event.path_len,
   85 |             "packet_hash": event.packet_hash,
   86 |             "snr": event.snr,
   87 |             "rssi": event.rssi,
   88 |         }
   89 |         if event.queued:
   90 |             await self._persist_companion_message(msg_dict)
   91 |         self._enqueue_frame(bytes([PUSH_CODE_MSG_WAITING]))
   92 | 
   93 |     async def _on_channel_data_event(self, event: ChannelDataEvent):
   94 |         msg_dict = {
   95 |             "sender_key": b"",
   96 |             "text": "",
   97 |             "timestamp": 0,
   98 |             "txt_type": 0,
   99 |             "is_channel": True,
  100 |             "channel_idx": event.channel_idx,
  101 |             "path_len": event.path_len,
  102 |             "packet_hash": event.packet_hash,
  103 |             "snr": event.snr,
  104 |             "rssi": event.rssi,
  105 |             "channel_data_type": event.data_type,
  106 |             "channel_data_payload": bytes(event.payload or b""),
  107 |         }
  108 |         if event.queued:
  109 |             await self._persist_companion_message(msg_dict)
  110 |         self._enqueue_frame(bytes([PUSH_CODE_MSG_WAITING]))
```

### Evidence 4: `src/openhop_core/node/dispatcher.py` lines 347–358

[Open source path](https://github.com/openhop-dev/openhop_core/blob/dev/src/openhop_core/node/dispatcher.py#L347-L358)

```text
  347 |     def _on_packet_received(
  348 |         self,
  349 |         data: bytes,
  350 |         rssi: Optional[int] = None,
  351 |         snr: Optional[float] = None,
  352 |     ) -> None:
  353 |         """Called by the radio when a packet comes in. rssi/snr are per-packet when provided."""
  354 |         try:
  355 |             loop = asyncio.get_running_loop()
  356 |             loop.create_task(self._process_received_packet(data, rssi, snr))
  357 |         except RuntimeError:
  358 |             self._log("No event loop running, cannot process received packet")
```
