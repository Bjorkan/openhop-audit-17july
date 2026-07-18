# BUG-047 — Local advert interval is saved and displayed but never used by the scheduler

[← Audit index](../README.md)

> Triple-verification verdict: **confirmed against the supplied snapshots**. This report was included only after three independent checks passed.

| Field | Value |
|---|---|
| Classification | **Confirmed defect** |
| Severity | 🟠 **Medium** |
| Confidence | **Triple-verified** |
| Area | Advert scheduling / API consistency |
| Components | OpenHop Repeater + Web UI |
| Audit date | 2026-07-17 |

## TL;DR

The API accepts and persists `advert_interval_minutes`, and stats expose it. The only periodic advert timer reads `send_advert_interval_hours`. Changing the local interval therefore appears successful and visible but has no runtime scheduling effect.

## Expected behavior

A user-visible advert interval must control a clearly identified advert scheduler, or the unused setting must be removed from API/UI.

## Required direction

1. Clarify local versus flood advert semantics and connect each setting to its intended scheduler.
2. Use one canonical field/unit per advert type across startup, reload, API, CLI, telemetry and documentation.
3. Return effective next-run information so the UI can verify the change.

## Triple verification

| Method | Check | Result | Observation |
|---|---|---|---|
| Static runtime trace | API writer and telemetry to scheduler | **Passed** | The accepted local-advert field is saved and displayed but never read by the timer, which uses a different interval. |
| Executable reproduction | Runtime reload | **Passed** | Reload retains the unrelated ten-hour scheduler value despite a one-minute local interval. |
| Active falsification | Actual timer decision | **Passed** | Two minutes after the last advert, the real scheduling decision sends nothing; no fallback consumes the configured local interval. |

The executable checks are preserved under [`docs/triple-verification/`](../docs/triple-verification/) and were rerun from clean Python processes for this edition. The third row is an explicit falsification/countercheck that searches for a guard, alternate adapter, normalization, documented contract or unreachable-state explanation that would invalidate the finding.

## Implementation plan

See [`implementation-plans/BUG-047/implementation_plan.md`](../implementation-plans/BUG-047/implementation_plan.md).

## Source evidence

### Evidence 1: `repeater/web/api_endpoints.py` lines 4091–4106

[Open source path](https://github.com/openhop-dev/openhop_repeater/blob/dev/repeater/web/api_endpoints.py#L4091-L4106)

```text
 4091 |                 applied.append(f"flood.advert.interval={hours}h")
 4092 | 
 4093 |             # Update local advert interval (minutes)
 4094 |             if "advert_interval_minutes" in data:
 4095 |                 mins = int(data["advert_interval_minutes"])
 4096 |                 if mins != 0 and (mins < 1 or mins > 10080):
 4097 |                     return self._error("Advert interval must be 0 (off) or 1-10080 minutes")
 4098 |                 self.config["repeater"]["advert_interval_minutes"] = mins
 4099 |                 applied.append(f"advert.interval={mins}m")
 4100 | 
 4101 |             # Update path hash mode (mesh: 0=1-byte, 1=2-byte, 2=3-byte)
 4102 |             if "path_hash_mode" in data:
 4103 |                 phm = int(data["path_hash_mode"])
 4104 |                 if phm not in (0, 1, 2):
 4105 |                     return self._error(
 4106 |                         "Path hash mode must be 0 (1-byte), 1 (2-byte), or 2 (3-byte)"
```
### Evidence 2: `repeater/engine.py` lines 1639–1649

[Open source path](https://github.com/openhop-dev/openhop_repeater/blob/dev/repeater/engine.py#L1639-L1649)

```text
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
```
### Evidence 3: `repeater/engine.py` lines 1690–1703

[Open source path](https://github.com/openhop-dev/openhop_repeater/blob/dev/repeater/engine.py#L1690-L1703)

```text
 1690 |                     await self._record_crc_errors_async()
 1691 |                     self.last_noise_measurement = current_time
 1692 | 
 1693 |                 # Check advert sending (every N hours)
 1694 |                 if self.send_advert_interval_hours > 0 and self.send_advert_func:
 1695 |                     interval_seconds = self.send_advert_interval_hours * 3600
 1696 |                     if current_time - self.last_advert_time >= interval_seconds:
 1697 |                         await self._send_periodic_advert_async()
 1698 |                         self.last_advert_time = current_time
 1699 | 
 1700 |                 # Prune expired entries from duplicate detection cache (every 60s)
 1701 |                 if current_time - self.last_cache_cleanup >= 60.0:
 1702 |                     self.cleanup_cache()
 1703 |                     self.last_cache_cleanup = current_time
```
### Evidence 4: `repeater/engine.py` lines 1794–1801

[Open source path](https://github.com/openhop-dev/openhop_repeater/blob/dev/repeater/engine.py#L1794-L1801)

```text
 1794 |             self.score_threshold = repeater_config.get("score_threshold", 0.3)
 1795 |             self.multi_acks = self._normalize_multi_acks(self.config)
 1796 |             self.send_advert_interval_hours = repeater_config.get("send_advert_interval_hours", 10)
 1797 |             self.cache_ttl = repeater_config.get("cache_ttl", 60)
 1798 |             self.max_flood_hops = repeater_config.get("max_flood_hops", 64)
 1799 |             self.neighbour_link_tracker.refresh_config(self.config)
 1800 |             self.loop_detect_mode = self._normalize_loop_detect_mode(
 1801 |                 self.config.get("mesh", {}).get("loop_detect", LOOP_DETECT_OFF)
```

