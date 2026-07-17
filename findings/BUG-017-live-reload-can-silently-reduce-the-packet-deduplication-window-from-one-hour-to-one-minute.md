# BUG-017 — Live reload can use a one-minute deduplication window when `cache_ttl` is absent or below the startup minimum

[← Audit index](../README.md)

> Reverification verdict: **Confirmed against the supplied snapshot.**

| Field | Value |
|---|---|
| Classification | **Confirmed defect** |
| Severity | **Medium** |
| Confidence | **Confirmed** |
| Area | Runtime configuration / packet deduplication |
| Components | OpenHop Repeater |
| Audit date | 2026-07-17 |
| Status | Open in supplied snapshot |

## TL;DR

Startup defaults and constrains `cache_ttl` to at least 300 seconds with a 3,600-second default. Runtime reload uses an unconstrained 60-second default.

## What happens now

Any live update that reloads the `repeater` section can change a running instance from one-hour deduplication to one minute when `cache_ttl` is absent. Configured values below five minutes are rejected at startup by clamping but accepted during reload. The same configuration therefore has different semantics before and after an unrelated live change.

## Expected behaviour / proposed direction

Initialization and reload must use the same parser, defaults and bounds.

## What needs to change

Create one `parse_runtime_repeater_settings()` function and assign its immutable result at startup and reload. Preserve the five-minute minimum and 3,600-second default.

## Reproduction / verification

The deeper focused check started with `cache_ttl=3600`, reloaded an empty repeater section and observed `cache_ttl=60`.

## Implementation plan

The former patch sketch has been replaced with a review-oriented plan covering the required repositories/files, implementation sequence, decisions to verify, regression tests, rollout and definition of done.

[Open `implementation_plan.md`](../implementation-plans/BUG-017/implementation_plan.md)


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

### Evidence 3: `repeater/config_manager.py` lines 286–307

[Open source path](https://github.com/openhop-dev/openhop_repeater/blob/dev/repeater/config_manager.py#L286-L307)

```text
  286 |             # Update each section
  287 |             for section in sections:
  288 |                 if section in self.config:
  289 |                     if section not in daemon_config:
  290 |                         daemon_config[section] = {}
  291 | 
  292 |                     # Deep copy the section to avoid reference issues
  293 |                     if isinstance(self.config[section], dict):
  294 |                         daemon_config[section].update(self.config[section])
  295 |                     else:
  296 |                         daemon_config[section] = self.config[section]
  297 | 
  298 |                     logger.debug(f"Live updated daemon config section: {section}")
  299 | 
  300 |             logger.info(f"Live updated daemon config sections: {', '.join(sections)}")
  301 | 
  302 |             # Also reload runtime config in RepeaterHandler if delays or repeater sections changed
  303 |             if self.daemon and hasattr(self.daemon, "repeater_handler"):
  304 |                 if any(s in ["delays", "repeater"] for s in sections):
  305 |                     if hasattr(self.daemon.repeater_handler, "reload_runtime_config"):
  306 |                         self.daemon.repeater_handler.reload_runtime_config()
  307 |                         logger.info("Reloaded RepeaterHandler runtime config")
```
