# BUG-048 — Mesh CLI flood advert interval writes a key the scheduler never reads

[← Audit index](../README.md)

> Triple-verification verdict: **confirmed against the supplied snapshots**. This report was included only after three independent checks passed.

| Field | Value |
|---|---|
| Classification | **Confirmed defect** |
| Severity | 🟠 **Medium** |
| Confidence | **Triple-verified** |
| Area | Mesh CLI / advert scheduling |
| Components | OpenHop Repeater |
| Audit date | 2026-07-17 |

## TL;DR

The command writes `flood_advert_interval_hours`, while startup, reload and the timer use `send_advert_interval_hours`. The command persists and displays its own orphan key but cannot change the active periodic advert interval.

## Expected behavior

The command must update the canonical scheduler field and report the effective runtime interval.

## Required direction

1. Rename the CLI writer/getter to `send_advert_interval_hours`, or migrate all consumers to a single newly named canonical key.
2. Migrate existing orphan values only with explicit precedence rules.
3. Share advert configuration parsing between CLI/API/startup/reload.

## Triple verification

| Method | Check | Result | Observation |
|---:|---|---|---|
| 1 | Static key trace | **Passed** | CLI writer and runtime reader use different names. |
| 2 | Public command persistence | **Passed** | The wrong key becomes 3 while the active key remains 10. |
| 3 | Runtime reload | **Passed** | The real reload method ignores the written key. |

The executable checks are preserved under [`docs/triple-verification/`](../docs/triple-verification/) and were rerun from clean Python processes for this edition.

## Implementation plan

See [`implementation-plans/BUG-048/implementation_plan.md`](../implementation-plans/BUG-048/implementation_plan.md).

## Source evidence

### Evidence 1: `repeater/handler_helpers/mesh_cli.py` lines 709–722

[Open source path](https://github.com/openhop-dev/openhop_repeater/blob/dev/repeater/handler_helpers/mesh_cli.py#L709-L722)

```text
  709 | 
  710 |             elif key == "flood.advert.interval":
  711 |                 hours = int(value)
  712 |                 if (hours > 0 and hours < 3) or hours > 168:
  713 |                     return "Error: interval range is 3-168 hours"
  714 |                 self.repeater_config["flood_advert_interval_hours"] = hours
  715 |                 saved, _ = self.config_manager.save_to_file()
  716 |                 self.config_manager.live_update_daemon(["repeater"])
  717 |                 return "OK"
  718 | 
  719 |             elif key == "flood.max":
  720 |                 max_val = int(value)
  721 |                 if max_val > 64:
  722 |                     return "Error: max 64"
```
### Evidence 2: `repeater/engine.py` lines 149–157

[Open source path](https://github.com/openhop-dev/openhop_repeater/blob/dev/repeater/engine.py#L149-L157)

```text
  149 |         self.multi_acks = self._normalize_multi_acks(config)
  150 |         self.max_flood_hops = config.get("repeater", {}).get("max_flood_hops", 64)
  151 |         self.send_advert_interval_hours = config.get("repeater", {}).get(
  152 |             "send_advert_interval_hours", 10
  153 |         )
  154 |         self.last_advert_time = time.time()
  155 |         self.loop_detect_mode = self._normalize_loop_detect_mode(
  156 |             config.get("mesh", {}).get("loop_detect", LOOP_DETECT_OFF)
  157 |         )
```
### Evidence 3: `repeater/engine.py` lines 1794–1801

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

