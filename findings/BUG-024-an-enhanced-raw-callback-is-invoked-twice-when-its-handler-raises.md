# BUG-024 — An enhanced raw callback is invoked twice when its handler raises

[← Audit index](../README.md)

> Triple-verification verdict: **confirmed against the supplied snapshots**. The finding survived an independent static runtime trace, executable reproduction and active falsification pass on 18 July 2026.

| Field | Value |
|---|---|
| Classification | **Confirmed defect** |
| Severity | **Medium** |
| Confidence | **Triple-verified** |
| Area | Callback dispatch / side effects |
| Components | OpenHop Core |
| Audit date | 2026-07-17 |
| Independent recheck | 2026-07-18 |
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

## Triple verification

| Method | Result | Record |
|---|---|---|
| Static runtime trace | **Passed** | The complete reachable path and exact quoted source excerpts in this report were revalidated byte-for-byte against the supplied source trees. |
| Executable reproduction | **Passed** | `test_bug_024_confirmed_handler_exception_is_misread_as_arity_failure_and_retried` in [`REVERIFICATION-CHECKS.py`](../docs/REVERIFICATION-CHECKS.py). |
| Active falsification | **Passed** | Fallback is triggered by any handler exception rather than pre-binding callback arity. See [`BASELINE-FALSIFICATION-CHECKS.py`](../docs/BASELINE-FALSIFICATION-CHECKS.py). |

The consolidated baseline matrix and captured results are in [`BASELINE-TRIPLE-VERIFICATION.md`](../docs/BASELINE-TRIPLE-VERIFICATION.md).

## Implementation plan

The former patch sketch has been replaced with a review-oriented plan covering the required repositories/files, implementation sequence, decisions to verify, regression tests, rollout and definition of done.

[Open `implementation_plan.md`](../implementation-plans/BUG-024/implementation_plan.md)


## Source references and excerpts

### Evidence 1: `src/openhop_core/node/dispatcher.py` lines 1082–1116

[Open source path](https://github.com/openhop-dev/openhop_core/blob/dev/src/openhop_core/node/dispatcher.py#L1082-L1116)

```text
 1082 |     async def _invoke_callback(self, cb, pkt: Packet) -> None:
 1083 |         if inspect.iscoroutinefunction(cb):
 1084 |             await cb(pkt)
 1085 |         else:
 1086 |             cb(pkt)
 1087 | 
 1088 |     async def _invoke_ack_listener(self, crc: int) -> None:
 1089 |         """Invoke ack-received listener (sync or async)."""
 1090 |         cb = self._ack_received_listener
 1091 |         if cb is None:
 1092 |             return
 1093 |         if inspect.iscoroutinefunction(cb):
 1094 |             await cb(crc)
 1095 |         else:
 1096 |             cb(crc)
 1097 | 
 1098 |     async def _invoke_enhanced_raw_callback(
 1099 |         self, callback, pkt: Packet, data: bytes, analysis: dict
 1100 |     ) -> None:
 1101 |         """Call raw packet callback with extra analysis data."""
 1102 |         try:
 1103 |             if inspect.iscoroutinefunction(callback):
 1104 |                 await callback(pkt, data, analysis)
 1105 |             else:
 1106 |                 callback(pkt, data, analysis)
 1107 |         except Exception as e:
 1108 |             self._log(f"Raw callback error: {e}")
 1109 |             # Fallback to original callback format
 1110 |             try:
 1111 |                 if inspect.iscoroutinefunction(callback):
 1112 |                     await callback(pkt, data)
 1113 |                 else:
 1114 |                     callback(pkt, data)
 1115 |             except Exception as e2:
 1116 |                 self._log(f"Fallback raw callback error: {e2}")
```
