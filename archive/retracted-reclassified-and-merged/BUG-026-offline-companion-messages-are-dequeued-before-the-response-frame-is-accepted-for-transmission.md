# RECLASSIFIED — former BUG-026 — destructive companion queue pop before transport enqueue

[← Reverification report](../../docs/REVERIFICATION-REPORT.md) · [← Audit index](../../README.md)

| Field | Value |
|---|---|
| Original classification | Confirmed defect |
| Reverified classification | **Documented delivery semantics; merged into possible enhancement 018** |
| Audit date | 2026-07-17 |

## What was verified

The implementation destructively pops the next offline message before placing the response frame in a bounded transport queue. A full transport queue can therefore discard the response after the offline item has been removed.

## Why this is not retained as a confirmed bug

The supplied contract explicitly describes `CMD_SYNC_NEXT_MESSAGE` as **“Pop next queued message.”** `MessageQueue.pop()` explicitly removes the oldest message, and the transport documents queue-full loss as **“natural backpressure shedding.”** The observed behavior is therefore consistent with the supplied at-most-once/destructive design, even though it is less reliable than an acknowledged delivery design.

Without stronger documentation promising retry-safe or acknowledged delivery, calling this a bug would substitute the auditor's preferred semantics for the project's stated semantics.

## Correct disposition

The stronger design remains valuable and is consolidated into [`POSSIBLE-ENHANCEMENT-018`](../../findings/POSSIBLE-ENHANCEMENT-018-use-an-acknowledged-outbox-for-companion-offline-delivery.md): stable message identities, reserve/commit/release semantics, explicit enqueue outcomes and restart-safe retry behavior.
