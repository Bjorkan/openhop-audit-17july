# POSSIBLE-ENHANCEMENT-020 — Possible enhancement — give message-queue entries stable identities and removal by token

[← Audit index](../README.md)

| Field | Value |
|---|---|
| Classification | **Possible enhancement** |
| Severity | **Enhancement** |
| Confidence | **High** |
| Area | Queue data model |
| Components | OpenHop Core + OpenHop Repeater |
| Audit date | 2026-07-17 |
| Status | Open in supplied snapshot |

## TL;DR

The queue exposes positional `pop()` and `pop_last()` only, while persistence operations need to commit removal of a specific entry after an await.

## What happens now

Positional removal assumes no interleaving and cannot express reservation or identity-safe commit.

## Expected behaviour / proposed direction

Store entries with stable IDs and expose `peek/reserve/remove(id)` operations.

## What needs to change

Supports safe async persistence, acknowledged delivery and precise diagnostics without relying on queue position.

## Suggested code change

> **Review warning:** the linked patch is an LLM-generated implementation sketch. It is intended to show the approximate change surface, not to be applied blindly. Rebase it onto the current source, add regression tests, and review concurrency, persistence and protocol implications.

[Open the suggested patch](../patches/POSSIBLE-ENHANCEMENT-020.patch)

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
