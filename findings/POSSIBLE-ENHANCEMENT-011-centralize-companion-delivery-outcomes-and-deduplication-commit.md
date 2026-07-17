# POSSIBLE-ENHANCEMENT-011 — Possible enhancement — centralize companion delivery outcomes and deduplication commit

[← Audit index](../README.md)

> Reverification verdict: **Factual premise confirmed; implementation remains optional.**

| Field | Value |
|---|---|
| Classification | **Possible enhancement** |
| Severity | **Enhancement** |
| Confidence | **High** |
| Area | Companion routing architecture |
| Components | OpenHop Repeater |
| Audit date | 2026-07-17 |
| Status | Open in supplied snapshot |

## TL;DR

PATH, protocol responses, login responses and local-candidate routing repeat different combinations of bridge fan-out, exception handling, consumption and deduplication.

## What happens now

Each branch decides independently when to mark delivery, whether authentication implies consumption and how bridge failures affect forwarding. The divergence directly enabled BUG-013 and BUG-014.

## Expected behaviour / proposed direction

Introduce a `CompanionDeliveryResult` and one helper that performs candidate selection, fan-out, error isolation and optional dedupe commit.

## What needs to change

Reduces branch-specific state bugs, makes policy behavior testable and gives logging consistent authenticated/failed/skipped counts.

## Implementation plan

The former patch sketch has been replaced with a review-oriented plan covering the required repositories/files, implementation sequence, decisions to verify, regression tests, rollout and definition of done.

[Open `implementation_plan.md`](../implementation-plans/POSSIBLE-ENHANCEMENT-011/implementation_plan.md)


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

### Evidence 2: `repeater/packet_router.py` lines 619–650

[Open source path](https://github.com/openhop-dev/openhop_repeater/blob/dev/repeater/packet_router.py#L619-L650)

```text
  619 |         elif payload_type == PathHandler.payload_type():
  620 |             # Always let PathHelper inspect/decrypt PATH first so out_path and bundled ACK state
  621 |             # are updated even when companion routing fan-out also happens for this packet.
  622 |             consumed = False
  623 |             if self.daemon.path_helper:
  624 |                 try:
  625 |                     consumed = (await self.daemon.path_helper.process_path_packet(packet)) is True
  626 |                 except Exception as e:
  627 |                     logger.debug(f"Path helper processing error: {e}")
  628 |             # The helper/bridge results decide ownership: a direct middle hop
  629 |             # that cannot authenticate remains eligible for engine forwarding,
  630 |             # while a local MAC-authenticated PATH is consumed below.
  631 |             dest_hash = packet.payload[0] if packet.payload else None
  632 |             companion_bridges = self._companion_bridges_for_packet(packet, metadata)
  633 |             if dest_hash is not None and dest_hash in companion_bridges:
  634 |                 if not self._was_delivered_to_companions(packet):
  635 |                     consumed = (
  636 |                         await self._fan_out_to_bridges(
  637 |                             packet, {dest_hash: companion_bridges[dest_hash]}, context="PATH"
  638 |                         )
  639 |                         or consumed
  640 |                     )
  641 |                     self._mark_delivered_to_companions(packet)
  642 |             elif companion_bridges and not self._was_delivered_to_companions(packet):
  643 |                 # Dest not in bridges: path-return with ephemeral dest (e.g. multi-hop login).
  644 |                 # Deliver to all bridges; each will try to decrypt and ignore if not relevant.
  645 |                 consumed = (
  646 |                     await self._fan_out_to_bridges(packet, companion_bridges, context="PATH")
  647 |                     or consumed
  648 |                 )
  649 |                 self._mark_delivered_to_companions(packet)
  650 |                 logger.debug(
```

### Evidence 3: `repeater/packet_router.py` lines 706–719

[Open source path](https://github.com/openhop-dev/openhop_repeater/blob/dev/repeater/packet_router.py#L706-L719)

```text
  706 |         elif payload_type == ProtocolResponseHandler.payload_type():
  707 |             # PAYLOAD_TYPE_PATH (0x08): protocol responses (telemetry, binary, etc.).
  708 |             # Deliver at most once per logical packet so the client is not spammed with duplicates,
  709 |             # but always deliver at a final hop (we are the destination). Do not set
  710 |             # processed_by_injection for a middle hop so the packet still reaches engine forwarding.
  711 |             companion_bridges = self._companion_bridges_for_packet(packet, metadata)
  712 |             final_hop = _is_direct_final_hop(packet)
  713 |             if companion_bridges and (final_hop or not self._was_delivered_to_companions(packet)):
  714 |                 await self._fan_out_to_bridges(packet, companion_bridges, context="RESPONSE")
  715 |                 self._mark_delivered_to_companions(packet)
  716 |             if companion_bridges and final_hop:
  717 |                 # DIRECT with empty path: we're the final hop, so consume after delivery.
  718 |                 processed_by_injection = True
  719 |                 self._record_for_ui(packet, metadata)
```
