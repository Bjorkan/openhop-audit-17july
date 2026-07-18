# BUG-014 — A failing companion bridge can shadow another local identity with the same destination hash

[← Audit index](../README.md)

> Triple-verification verdict: **confirmed against the supplied snapshots**. The finding survived an independent static runtime trace, executable reproduction and active falsification pass on 18 July 2026.

| Field | Value |
|---|---|
| Classification | **Confirmed defect** |
| Severity | **High** |
| Confidence | **Triple-verified** |
| Area | Local identity routing / collision handling |
| Components | OpenHop Repeater |
| Audit date | 2026-07-17 |
| Independent recheck | 2026-07-18 |
| Status | Open in supplied snapshot |

## TL;DR

The collision-handling helper promises to offer a packet to every local candidate sharing the one-byte destination hash, but an exception from the companion bridge aborts the method before the room-server or repeater identity is tried.

## What happens now

`_consume_via_local_candidates()` directly awaits the companion bridge without the exception isolation used by `_fan_out_to_bridges()`. If that bridge raises, the helper candidate is skipped and the route task fails, even though it may be the identity that can authenticate the packet.

## Expected behaviour / proposed direction

Each local candidate should be isolated. One broken candidate must not prevent another candidate with the same one-byte hash from attempting decryption.

## What needs to change

Use one shared candidate-delivery helper that catches/logs per-candidate failures and continues. Return true if any candidate authenticates.

## Reproduction / verification

The deeper focused check supplied a raising companion bridge and a helper that would authenticate. The exception escaped and the helper was never called.

## Triple verification

| Method | Result | Record |
|---|---|---|
| Static runtime trace | **Passed** | The complete reachable path and exact quoted source excerpts in this report were revalidated byte-for-byte against the supplied source trees. |
| Executable reproduction | **Passed** | `test_bug_014_confirmed_bridge_exception_prevents_colliding_helper_candidate` in [`REVERIFICATION-CHECKS.py`](../docs/REVERIFICATION-CHECKS.py). |
| Active falsification | **Passed** | The local-candidate helper has no per-candidate exception isolation or continuation fallback. See [`BASELINE-FALSIFICATION-CHECKS.py`](../docs/BASELINE-FALSIFICATION-CHECKS.py). |

The consolidated baseline matrix and captured results are in [`BASELINE-TRIPLE-VERIFICATION.md`](../docs/BASELINE-TRIPLE-VERIFICATION.md).

## Implementation plan

The former patch sketch has been replaced with a review-oriented plan covering the required repositories/files, implementation sequence, decisions to verify, regression tests, rollout and definition of done.

[Open `implementation_plan.md`](../implementation-plans/BUG-014/implementation_plan.md)


## Source references and excerpts

### Evidence 1: `repeater/packet_router.py` lines 276–328

[Open source path](https://github.com/openhop-dev/openhop_repeater/blob/dev/repeater/packet_router.py#L276-L328)

```text
  276 |     async def _fan_out_to_bridges(self, packet, bridges, *, context: str) -> bool:
  277 |         """Offer packet to each bridge; True if any bridge authenticated it.
  278 | 
  279 |         Accepts a dict of bridges — pass a single-entry dict for targeted delivery
  280 |         to the bridge that owns ``dest_hash``. A bridge that raises is logged and
  281 |         skipped; ``result.authenticated`` is read directly (every bridge returns a
  282 |         HandlerResult) so a broken contract surfaces instead of being hidden.
  283 |         """
  284 |         authenticated = False
  285 |         for bridge in bridges.values():
  286 |             try:
  287 |                 result = await bridge.process_received_packet(packet)
  288 |             except Exception as e:
  289 |                 logger.debug("Companion bridge %s error: %s", context, e)
  290 |                 continue
  291 |             if result.authenticated is True:
  292 |                 authenticated = True
  293 |         return authenticated
  294 | 
  295 |     async def _consume_via_local_candidates(
  296 |         self, packet, metadata: dict, dest_hash, helper, process_method_name: str
  297 |     ) -> bool:
  298 |         """Try every local candidate that shares ``dest_hash`` and report consumption.
  299 | 
  300 |         The on-air destination hash is only one byte, so several local identities
  301 |         can share it. The candidates are the companion bridge registered at
  302 |         ``dest_hash`` and the room-server / repeater identity registered in
  303 |         ``helper`` (login, text, or protocol-request) at the same hash. Both are
  304 |         offered the packet; the one whose key MAC-verifies it consumes it, the
  305 |         other fails HMAC and no-ops.
  306 | 
  307 |         Returns True only when at least one candidate authenticated (decrypted)
  308 |         the packet. Consuming solely on authenticated handling is what lets a
  309 |         one-byte prefix collision with a remote node — or a forged packet — fall
  310 |         through to the forwarding engine instead of being swallowed.
  311 |         """
  312 |         companion_bridges = self._companion_bridges_for_packet(packet, metadata)
  313 |         helper_handlers = getattr(helper, "handlers", {}) if helper else {}
  314 |         has_companion = dest_hash is not None and dest_hash in companion_bridges
  315 |         has_local_identity = dest_hash is not None and dest_hash in helper_handlers
  316 | 
  317 |         consumed = False
  318 |         if has_companion:
  319 |             bridge_result = await companion_bridges[dest_hash].process_received_packet(packet)
  320 |             if bridge_result.authenticated:
  321 |                 consumed = True
  322 |         # Offer to the room-server / repeater identity when it shares the hash
  323 |         # (collision) or when no local companion claims it at all (normal
  324 |         # server-owned + remote-forward handling).
  325 |         if helper and (has_local_identity or not has_companion):
  326 |             if await getattr(helper, process_method_name)(packet):
  327 |                 consumed = True
  328 |         return consumed
```
