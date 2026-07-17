# POSSIBLE-ENHANCEMENT-012 — Possible enhancement — share one duplicate-grouping helper for normal and raw receive paths

[← Audit index](../README.md)

> Reverification verdict: **Factual premise confirmed; implementation remains optional.**

| Field | Value |
|---|---|
| Classification | **Possible enhancement** |
| Severity | **Enhancement** |
| Confidence | **High** |
| Area | Packet history code reuse |
| Components | OpenHop Repeater |
| Audit date | 2026-07-17 |
| Status | Open in supplied snapshot |

## TL;DR

Two code paths independently find the original packet, initialize `duplicates`, apply-or-omit caps and decide whether to append a standalone record.

## What happens now

The branches have already drifted: only the normal path applies the cap. Future changes to counters or omission metadata would require synchronized edits.

## Expected behaviour / proposed direction

Extract one helper responsible for grouping, capping and fallback insertion.

## What needs to change

Removes duplicated conditionals and provides one unit-testable place for memory bounds and UI metadata.

## Implementation plan

The former patch sketch has been replaced with a review-oriented plan covering the required repositories/files, implementation sequence, decisions to verify, regression tests, rollout and definition of done.

[Open `implementation_plan.md`](../implementation-plans/POSSIBLE-ENHANCEMENT-012/implementation_plan.md)


## Source references and excerpts

### Evidence 1: `repeater/engine.py` lines 568–583

[Open source path](https://github.com/openhop-dev/openhop_repeater/blob/dev/repeater/engine.py#L568-L583)

```text
  568 |         # If this is a duplicate, try to attach it to the original packet
  569 |         if is_dupe and len(self.recent_packets) > 0:
  570 |             prev_pkt = self._recent_hash_index.get(packet_record["packet_hash"])
  571 |             if prev_pkt is not None:
  572 |                 # Add duplicate to original packet's duplicate list
  573 |                 if "duplicates" not in prev_pkt:
  574 |                     prev_pkt["duplicates"] = []
  575 |                 if len(prev_pkt["duplicates"]) < self.max_duplicates_per_packet:
  576 |                     prev_pkt["duplicates"].append(packet_record)
  577 |                 # Don't add duplicate to main list, just track in original
  578 |             else:
  579 |                 # Original not found, add as regular packet
  580 |                 self._append_recent_packet(packet_record)
  581 |         else:
  582 |             # Not a duplicate or first occurrence
  583 |             self._append_recent_packet(packet_record)
```

### Evidence 2: `repeater/engine.py` lines 655–732

[Open source path](https://github.com/openhop-dev/openhop_repeater/blob/dev/repeater/engine.py#L655-L732)

```text
  655 |     def record_duplicate(self, packet: Packet, rssi: int = 0, snr: float = 0.0) -> None:
  656 |         """Record a known-duplicate packet for UI/storage visibility without forwarding.
  657 | 
  658 |         Called by the raw_packet_subscriber path so that path variants blocked
  659 |         by the Dispatcher's payload-based dedup still appear in the UI.
  660 |         """
  661 |         self.rx_count += 1
  662 |         route_type = packet.header & PH_ROUTE_MASK
  663 |         if route_type in (ROUTE_TYPE_FLOOD, ROUTE_TYPE_TRANSPORT_FLOOD):
  664 |             self.recv_flood_count += 1
  665 |             self.flood_dup_count += 1
  666 |         elif route_type in (ROUTE_TYPE_DIRECT, ROUTE_TYPE_TRANSPORT_DIRECT):
  667 |             self.recv_direct_count += 1
  668 |             self.direct_dup_count += 1
  669 | 
  670 |         header_info = PacketHeaderUtils.parse_header(packet.header)
  671 |         payload_type = header_info["payload_type"]
  672 |         route_type_parsed = header_info["route_type"]
  673 | 
  674 |         original_path_hashes = packet.get_path_hashes_hex()
  675 |         path_hash_size = packet.get_path_hash_size()
  676 |         path_hash = self._path_hash_display(original_path_hashes)
  677 |         src_hash, dst_hash = self._packet_record_src_dst(packet, payload_type)
  678 |         pkt_hash_full = packet.calculate_packet_hash().hex().upper()
  679 | 
  680 |         frame_len = packet.get_raw_length() if hasattr(packet, "get_raw_length") else 0
  681 |         score = flood_rx_metrics(
  682 |             frame_len,
  683 |             snr,
  684 |             self.radio_config["spreading_factor"],
  685 |             self.radio_config["bandwidth"],
  686 |             self.radio_config["coding_rate"],
  687 |             self.radio_config["preamble_length"],
  688 |         ).score
  689 |         self.neighbour_link_tracker.observe(
  690 |             packet,
  691 |             route_type=route_type,
  692 |             payload_type=payload_type,
  693 |             rssi=float(rssi),
  694 |             snr=float(snr),
  695 |             score=score,
  696 |             is_duplicate=True,
  697 |         )
  698 | 
  699 |         packet_record = self._build_packet_record(
  700 |             packet,
  701 |             payload_type,
  702 |             route_type_parsed,
  703 |             rssi,
  704 |             snr,
  705 |             original_path_hashes,
  706 |             path_hash_size,
  707 |             path_hash,
  708 |             src_hash,
  709 |             dst_hash,
  710 |             transmitted=False,
  711 |             drop_reason=DropReason.DUPLICATE,
  712 |             is_duplicate=True,
  713 |             packet_hash=pkt_hash_full,
  714 |         )
  715 | 
  716 |         if self.storage:
  717 |             try:
  718 |                 self.storage.record_packet(packet_record, skip_mqtt_if_invalid=False)
  719 |             except Exception as e:
  720 |                 logger.error(f"Failed to store duplicate record: {e}")
  721 | 
  722 |         # Group under original in recent_packets
  723 |         if len(self.recent_packets) > 0:
  724 |             prev_pkt = self._recent_hash_index.get(packet_record["packet_hash"])
  725 |             if prev_pkt is not None:
  726 |                 if "duplicates" not in prev_pkt:
  727 |                     prev_pkt["duplicates"] = []
  728 |                 prev_pkt["duplicates"].append(packet_record)
  729 |             else:
  730 |                 self._append_recent_packet(packet_record)
  731 |         else:
  732 |             self._append_recent_packet(packet_record)
```
