# BUG-024 — An enhanced raw callback is invoked twice when its handler raises

[← Audit index](../README.md)

| Field | Value |
|---|---|
| Classification | **Confirmed defect** |
| Severity | **Medium** |
| Confidence | **Confirmed** |
| Area | Callback dispatch / side effects |
| Components | OpenHop Core |
| Audit date | 2026-07-17 |
| Status | Open in supplied snapshot |

## TL;DR

Any exception from the three-argument callback is treated as if the callback merely had the older two-argument signature, so the same callback is invoked a second time.

## What happens now

A valid enhanced callback may store data, increment counters or enqueue work and then raise. Dispatcher logs the failure and calls it again with two arguments. Side effects can be duplicated, and the second call can execute a different compatibility branch inside variadic callbacks.

## Expected behaviour / proposed direction

Signature compatibility should be resolved before invocation. A runtime exception from the chosen callback form must be reported once, not interpreted as arity mismatch.

## What needs to change

Inspect/bind the callable signature before the call, or register callback capability explicitly. Invoke exactly once and separately catch handler errors.

## Reproduction / verification

The deeper focused check used a variadic callback that increments a counter and raises only on the enhanced call. The current helper invoked it twice.

## Implementation plan

The former patch sketch has been replaced with a review-oriented plan covering the required repositories/files, implementation sequence, decisions to verify, regression tests, rollout and definition of done.

[Open `implementation_plan.md`](../implementation-plans/BUG-024/implementation_plan.md)


## Source references and excerpts

### Evidence 1: `src/openhop_core/node/dispatcher.py` lines 772–806

[Open source path](https://github.com/openhop-dev/openhop_core/blob/dev/src/openhop_core/node/dispatcher.py#L772-L806)

```text
  772 |     async def _invoke_callback(self, cb, pkt: Packet) -> None:
  773 |         if inspect.iscoroutinefunction(cb):
  774 |             await cb(pkt)
  775 |         else:
  776 |             cb(pkt)
  777 | 
  778 |     async def _invoke_ack_listener(self, crc: int) -> None:
  779 |         """Invoke ack-received listener (sync or async)."""
  780 |         cb = self._ack_received_listener
  781 |         if cb is None:
  782 |             return
  783 |         if inspect.iscoroutinefunction(cb):
  784 |             await cb(crc)
  785 |         else:
  786 |             cb(crc)
  787 | 
  788 |     async def _invoke_enhanced_raw_callback(
  789 |         self, callback, pkt: Packet, data: bytes, analysis: dict
  790 |     ) -> None:
  791 |         """Call raw packet callback with extra analysis data."""
  792 |         try:
  793 |             if inspect.iscoroutinefunction(callback):
  794 |                 await callback(pkt, data, analysis)
  795 |             else:
  796 |                 callback(pkt, data, analysis)
  797 |         except Exception as e:
  798 |             self._log(f"Raw callback error: {e}")
  799 |             # Fallback to original callback format
  800 |             try:
  801 |                 if inspect.iscoroutinefunction(callback):
  802 |                     await callback(pkt, data)
  803 |                 else:
  804 |                     callback(pkt, data)
  805 |             except Exception as e2:
  806 |                 self._log(f"Fallback raw callback error: {e2}")
```
