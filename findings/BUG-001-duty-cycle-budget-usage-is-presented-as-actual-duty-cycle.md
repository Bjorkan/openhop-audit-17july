# BUG-001 — Duty-cycle budget usage is presented as actual duty cycle

[← Audit index](../README.md)

> Triple-verification verdict: **confirmed against the supplied snapshots**. The finding survived an independent static runtime trace, executable reproduction and active falsification pass on 18 July 2026.

| Field | Value |
|---|---|
| Classification | **Confirmed defect** |
| Severity | **Medium** |
| Confidence | **Triple-verified** |
| Area | Telemetry and dashboard |
| Components | OpenHop Repeater + Web UI |
| Audit date | 2026-07-17 |
| Independent recheck | 2026-07-18 |
| Status | Open in supplied snapshot |

## TL;DR

`utilization_percent` is the percentage of the configured allowance that has been consumed, while the UI places it next to the configured duty-cycle percentage as though both use the same denominator. A value such as `76.2% / 10.0%` can therefore mean an actual duty cycle of only 7.62%.

## What happens now

The backend divides rolling airtime by `max_airtime_per_minute`. The dashboard labels that result as “Duty Cycle” and compares it with `max_airtime_percent`, while Glass and storage publish the same ambiguous field. This also causes progress calculations to normalize an already-normalized value a second time.

## Expected behaviour / proposed direction

The data contract should expose both `actual_duty_percent = current_airtime_ms / 60000 * 100` and `budget_used_percent = current_airtime_ms / max_airtime_ms * 100`. UI labels and external telemetry should use the matching value.

## What needs to change

Introduce an explicit airtime snapshot with unambiguous names, preserve any legacy field temporarily with a deprecation note, and update the dashboard/Glass/storage consumers together.

## Reproduction / verification

Focused check reproduced 4,572 ms used from a 6,000 ms allowance: backend reports 76.2%, while actual duty cycle is 7.62%.

See [`docs/REVERIFICATION-CHECKS.md`](../docs/REVERIFICATION-CHECKS.md) and the executable check script.

## Triple verification

| Method | Result | Record |
|---|---|---|
| Static runtime trace | **Passed** | The complete reachable path and exact quoted source excerpts in this report were revalidated byte-for-byte against the supplied source trees. |
| Executable reproduction | **Passed** | `test_bug_001_confirmed_duty_budget_vs_actual_duty_and_ui_double_normalization` in [`REVERIFICATION-CHECKS.py`](../docs/REVERIFICATION-CHECKS.py). |
| Active falsification | **Passed** | No alternate actual-duty field or consumer correction exists; the UI normalizes budget utilization again. See [`BASELINE-FALSIFICATION-CHECKS.py`](../docs/BASELINE-FALSIFICATION-CHECKS.py). |

The consolidated baseline matrix and captured results are in [`BASELINE-TRIPLE-VERIFICATION.md`](../docs/BASELINE-TRIPLE-VERIFICATION.md).

## Implementation plan

The former patch sketch has been replaced with a review-oriented plan covering the required repositories/files, implementation sequence, decisions to verify, regression tests, rollout and definition of done.

[Open `implementation_plan.md`](../implementation-plans/BUG-001/implementation_plan.md)


## Source references and excerpts

Duty-cycle labels and calculations in the compiled dashboard are captured in [`docs/UI-SOURCE-EXCERPTS.md`](../docs/UI-SOURCE-EXCERPTS.md).

### Evidence 1: `repeater/airtime.py` lines 104–116

[Open source path](https://github.com/openhop-dev/openhop_repeater/blob/dev/repeater/airtime.py#L104-L116)

```text
  104 |     def get_stats(self) -> dict:
  105 |         now = time.time()
  106 |         self.tx_history = [(ts, at) for ts, at in self.tx_history if now - ts < self.window_size]
  107 | 
  108 |         current_airtime = sum(at for _, at in self.tx_history)
  109 |         utilization = (current_airtime / self.max_airtime_per_minute) * 100
  110 | 
  111 |         return {
  112 |             "current_airtime_ms": current_airtime,
  113 |             "max_airtime_ms": self.max_airtime_per_minute,
  114 |             "utilization_percent": utilization,
  115 |             "total_airtime_ms": self.total_airtime_ms,
  116 |             "total_rx_airtime_ms": self.total_rx_airtime_ms,
```

### Evidence 2: `repeater/engine.py` lines 1577–1655

[Open source path](https://github.com/openhop-dev/openhop_repeater/blob/dev/repeater/engine.py#L1577-L1655)

```text
 1577 |         uptime_seconds = time.time() - self.start_time
 1578 | 
 1579 |         # Get config sections
 1580 |         repeater_config = self.config.get("repeater", {})
 1581 |         duty_cycle_config = self.config.get("duty_cycle", {})
 1582 |         delays_config = self.config.get("delays", {})
 1583 | 
 1584 |         max_airtime_ms = duty_cycle_config.get("max_airtime_per_minute", 3600)
 1585 |         max_duty_cycle_percent = (max_airtime_ms / 60000) * 100  # 60000ms = 1 minute
 1586 | 
 1587 |         # Calculate actual hourly rates (packets in last 3600 seconds)
 1588 |         now = time.time()
 1589 |         packets_last_hour = [p for p in self.recent_packets if now - p["timestamp"] < 3600]
 1590 |         rx_per_hour = len(packets_last_hour)
 1591 |         forwarded_per_hour = sum(1 for p in packets_last_hour if p.get("transmitted", False))
 1592 | 
 1593 |         # Use cached value sampled by the background timer to avoid serial I/O on stats requests.
 1594 |         noise_floor_dbm = self.get_cached_noise_floor()
 1595 | 
 1596 |         # Get CRC error count from radio hardware
 1597 |         radio = self.dispatcher.radio if self.dispatcher else None
 1598 |         crc_error_count = getattr(radio, "crc_error_count", 0) if radio else 0
 1599 | 
 1600 |         # Get neighbors from database
 1601 |         neighbors = self.storage.get_neighbors() if self.storage else {}
 1602 | 
 1603 |         # Format local_hash respecting path_hash_mode
 1604 |         phm = self.config.get("mesh", {}).get("path_hash_mode", 0)
 1605 |         _bc = {0: 1, 1: 2, 2: 3}.get(phm, 1)
 1606 |         _hc = _bc * 2
 1607 |         _val = int.from_bytes(bytes(self.local_hash_bytes[:_bc]), "big")
 1608 |         local_hash_str = f"0x{_val:0{_hc}x}"
 1609 | 
 1610 |         stats = {
 1611 |             "local_hash": local_hash_str,
 1612 |             "duplicate_cache_size": len(self.seen_packets),
 1613 |             "cache_ttl": self.cache_ttl,
 1614 |             "rx_count": self.rx_count,
 1615 |             "forwarded_count": self.forwarded_count,
 1616 |             "dropped_count": self.dropped_count,
 1617 |             "recv_flood_count": self.recv_flood_count,
 1618 |             "recv_direct_count": self.recv_direct_count,
 1619 |             "sent_flood_count": self.sent_flood_count,
 1620 |             "sent_direct_count": self.sent_direct_count,
 1621 |             "flood_dup_count": self.flood_dup_count,
 1622 |             "direct_dup_count": self.direct_dup_count,
 1623 |             "rx_per_hour": rx_per_hour,
 1624 |             "forwarded_per_hour": forwarded_per_hour,
 1625 |             "recent_packets": list(self.recent_packets),
 1626 |             "neighbors": neighbors,
 1627 |             "uptime_seconds": uptime_seconds,
 1628 |             "noise_floor_dbm": noise_floor_dbm,
 1629 |             "crc_error_count": crc_error_count,
 1630 |             # Add configuration data
 1631 |             "config": {
 1632 |                 "node_name": repeater_config.get("node_name", "Unknown"),
 1633 |                 "repeater": {
 1634 |                     "mode": repeater_config.get("mode", "forward"),
 1635 |                     "use_score_for_tx": repeater_config.get("use_score_for_tx", False),
 1636 |                     "score_threshold": repeater_config.get("score_threshold", 0.3),
 1637 |                     "send_advert_interval_hours": repeater_config.get(
 1638 |                         "send_advert_interval_hours", 10
 1639 |                     ),
 1640 |                     "latitude": repeater_config.get("latitude", 0.0),
 1641 |                     "longitude": repeater_config.get("longitude", 0.0),
 1642 |                     "max_flood_hops": repeater_config.get("max_flood_hops", 64),
 1643 |                     "advert_interval_minutes": repeater_config.get("advert_interval_minutes", 120),
 1644 |                     "advert_rate_limit": repeater_config.get("advert_rate_limit", {}),
 1645 |                     "advert_penalty_box": repeater_config.get("advert_penalty_box", {}),
 1646 |                     "advert_adaptive": repeater_config.get("advert_adaptive", {}),
 1647 |                 },
 1648 |                 "radio": self.config.get(
 1649 |                     "radio", {}
 1650 |                 ),  # Read from live config, not cached radio_config
 1651 |                 "duty_cycle": {
 1652 |                     "max_airtime_percent": max_duty_cycle_percent,
 1653 |                     "enforcement_enabled": duty_cycle_config.get("enforcement_enabled", True),
 1654 |                 },
 1655 |                 "delays": {
```

### Evidence 3: `repeater/data_acquisition/glass_handler.py` lines 304–325

[Open source path](https://github.com/openhop-dev/openhop_repeater/blob/dev/repeater/data_acquisition/glass_handler.py#L304-L325)

```text
  304 |             "config_hash": self._compute_config_hash(self.config),
  305 |             "cert_expires_at": self._cert_expires_at,
  306 |             "system": self._collect_system_stats(),
  307 |             "radio": {
  308 |                 "frequency": int(self.config.get("radio", {}).get("frequency", 0)),
  309 |                 "spreading_factor": int(self.config.get("radio", {}).get("spreading_factor", 7)),
  310 |                 "bandwidth": int(self.config.get("radio", {}).get("bandwidth", 0)),
  311 |                 "tx_power": int(self.config.get("radio", {}).get("tx_power", 0)),
  312 |                 "noise_floor_dbm": stats.get("noise_floor_dbm"),
  313 |                 "mode": self.config.get("repeater", {}).get("mode", "forward"),
  314 |             },
  315 |             "counters": {
  316 |                 "rx_total": int(stats.get("rx_count", 0)),
  317 |                 "tx_total": max(0, tx_total),
  318 |                 "forwarded": int(stats.get("forwarded_count", 0)),
  319 |                 "dropped": int(stats.get("dropped_count", 0)),
  320 |                 "duplicates": int(stats.get("flood_dup_count", 0))
  321 |                 + int(stats.get("direct_dup_count", 0)),
  322 |                 "airtime_percent": float(stats.get("utilization_percent", 0.0)),
  323 |             },
  324 |             "settings": settings_snapshot,
  325 |             "command_results": command_results,
```

### Evidence 4: `repeater/data_acquisition/storage_collector.py` lines 140–175

[Open source path](https://github.com/openhop-dev/openhop_repeater/blob/dev/repeater/data_acquisition/storage_collector.py#L140-L175)

```text
  140 |                 "packets_sent": 0,
  141 |                 "packets_received": 0,
  142 |                 "errors": 0,
  143 |                 "queue_len": 0,
  144 |             }
  145 | 
  146 |         uptime_secs = int(time.time() - self.repeater_handler.start_time)
  147 | 
  148 |         # Get airtime stats
  149 |         airtime_stats = self.repeater_handler.airtime_mgr.get_stats()
  150 | 
  151 |         # Get latest noise floor from database
  152 |         noise_floor = None
  153 |         try:
  154 |             recent_noise = self.sqlite_handler.get_noise_floor_history(hours=0.5, limit=1)
  155 |             if recent_noise and len(recent_noise) > 0:
  156 |                 noise_floor = recent_noise[-1].get("noise_floor_dbm")
  157 |         except Exception as e:
  158 |             logger.debug(f"Could not fetch noise floor: {e}")
  159 | 
  160 |         stats = {
  161 |             "uptime_secs": uptime_secs,
  162 |             "packets_sent": self.repeater_handler.forwarded_count,
  163 |             "packets_received": self.repeater_handler.rx_count,
  164 |             "errors": 0,
  165 |             "queue_len": 0,  # N/A for Python repeater
  166 |         }
  167 | 
  168 |         # Add airtime stats
  169 |         if airtime_stats:
  170 |             stats["tx_air_secs"] = airtime_stats["total_airtime_ms"] / 1000
  171 |             stats["current_airtime_ms"] = airtime_stats["current_airtime_ms"]
  172 |             stats["utilization_percent"] = airtime_stats["utilization_percent"]
  173 | 
  174 |         # Add noise floor if available
  175 |         if noise_floor is not None:
```
