# POSSIBLE-ENHANCEMENT-013 — Possible enhancement — parse runtime settings once for both initialization and live reload

[← Audit index](../README.md)

> Reverification verdict: **Factual premise confirmed; implementation remains optional.**

| Field | Value |
|---|---|
| Classification | **Possible enhancement** |
| Severity | **Enhancement** |
| Confidence | **High** |
| Area | Runtime configuration architecture |
| Components | OpenHop Repeater |
| Audit date | 2026-07-17 |
| Status | Open in supplied snapshot |

## TL;DR

Repeater initialization and `reload_runtime_config()` separately encode defaults, bounds and normalization for the same settings.

## What happens now

The two blocks already disagree about `cache_ttl`; similar drift can recur for score thresholds, advert intervals, multi-ACKs and mesh modes.

## Expected behaviour / proposed direction

Build a validated immutable `RepeaterRuntimeSettings` snapshot from config and apply it in both places.

## What needs to change

Makes startup/reload parity automatic, centralizes migration warnings and supports table-driven tests for every field.

## Implementation plan

The former patch sketch has been replaced with a review-oriented plan covering the required repositories/files, implementation sequence, decisions to verify, regression tests, rollout and definition of done.

[Open `implementation_plan.md`](../implementation-plans/POSSIBLE-ENHANCEMENT-013/implementation_plan.md)


## Source references and excerpts

### Evidence 1: `repeater/engine.py` lines 124–137

[Open source path](https://github.com/openhop-dev/openhop_repeater/blob/dev/repeater/engine.py#L124-L137)

```text
  124 |         self.config = config
  125 |         self.dispatcher = dispatcher
  126 |         self.local_hash = local_hash
  127 |         self.local_hash_bytes = local_hash_bytes or bytes([local_hash])
  128 |         self.send_advert_func = send_advert_func
  129 |         self.airtime_mgr = AirtimeManager(config)
  130 |         self.policy_engine = PolicyEngine.from_runtime_config(config)
  131 |         self.seen_packets = OrderedDict()
  132 |         self.cache_ttl = max(
  133 |             300, config.get("repeater", {}).get("cache_ttl", 3600)
  134 |         )  # Min 5 min, default 1 hour
  135 |         self.max_cache_size = 1000
  136 |         self.max_duplicates_per_packet = 20
  137 |         self.tx_delay_factor = config.get("delays", {}).get("tx_delay_factor", 1.0)
```

### Evidence 2: `repeater/engine.py` lines 1782–1817

[Open source path](https://github.com/openhop-dev/openhop_repeater/blob/dev/repeater/engine.py#L1782-L1817)

```text
 1782 |     def reload_runtime_config(self):
 1783 |         """Reload runtime configuration from self.config (called after live config updates)."""
 1784 |         try:
 1785 |             # Refresh delay factors
 1786 |             self.tx_delay_factor = self.config.get("delays", {}).get("tx_delay_factor", 1.0)
 1787 |             self.direct_tx_delay_factor = self.config.get("delays", {}).get(
 1788 |                 "direct_tx_delay_factor", 0.5
 1789 |             )
 1790 | 
 1791 |             # Refresh repeater settings
 1792 |             repeater_config = self.config.get("repeater", {})
 1793 |             self.use_score_for_tx = repeater_config.get("use_score_for_tx", False)
 1794 |             self.score_threshold = repeater_config.get("score_threshold", 0.3)
 1795 |             self.multi_acks = self._normalize_multi_acks(self.config)
 1796 |             self.send_advert_interval_hours = repeater_config.get("send_advert_interval_hours", 10)
 1797 |             self.cache_ttl = repeater_config.get("cache_ttl", 60)
 1798 |             self.max_flood_hops = repeater_config.get("max_flood_hops", 64)
 1799 |             self.neighbour_link_tracker.refresh_config(self.config)
 1800 |             self.loop_detect_mode = self._normalize_loop_detect_mode(
 1801 |                 self.config.get("mesh", {}).get("loop_detect", LOOP_DETECT_OFF)
 1802 |             )
 1803 | 
 1804 |             with self.neighbour_link_tracker.lock:
 1805 |                 now_monotonic = time.monotonic()
 1806 |                 self.neighbour_link_tracker.purge_expired_locked(now_monotonic)
 1807 |                 while (
 1808 |                     len(self.neighbour_link_tracker.links) > self.neighbour_link_tracker.max_entries
 1809 |                 ):
 1810 |                     self.neighbour_link_tracker.evict_stalest_locked()
 1811 | 
 1812 |             # Note: Radio config changes require restart as they affect hardware
 1813 |             # Note: Airtime manager has its own config reference that gets updated
 1814 | 
 1815 |             logger.info("Runtime configuration reloaded successfully")
 1816 |         except Exception as e:
 1817 |             logger.error(f"Error reloading runtime config: {e}")
```
