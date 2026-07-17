# BUG-004 — Live radio changes leave airtime estimation on the old modulation

[← Audit index](../README.md)

| Field | Value |
|---|---|
| Classification | **Confirmed defect** |
| Severity | **High** |
| Confidence | **Confirmed** |
| Area | Radio configuration / duty-cycle enforcement |
| Components | OpenHop Core + OpenHop Repeater |
| Audit date | 2026-07-17 |
| Status | Open in supplied snapshot |

## TL;DR

Frequency/modulation changes can be applied to hardware while airtime accounting continues using the startup spreading factor, bandwidth, coding rate and preamble.

## What happens now

`AirtimeManager` copies radio values during construction. `ConfigManager` reconfigures the hardware and updates `repeater_handler.radio_config`, but it does not refresh the manager. The comment that the manager “has its own config reference that gets updated” is insufficient because calculations use cached scalar attributes.

## Expected behaviour / proposed direction

Hardware modulation and the parameters used to calculate airtime must be updated in the same successful operation.

## What needs to change

Reload airtime parameters only after hardware configuration succeeds; on failure keep both the old hardware and old accounting snapshot, or require restart.

## Reproduction / verification

Focused check changed SF7 to SF12. The manager kept returning 97.536 ms for a 50-byte packet while the shared estimator returned 2,301.952 ms for SF12.

See [`docs/REPRODUCTION-CHECKS.md`](../docs/REPRODUCTION-CHECKS.md) and the executable check script.

## Implementation plan

The former patch sketch has been replaced with a review-oriented plan covering the required repositories/files, implementation sequence, decisions to verify, regression tests, rollout and definition of done.

[Open `implementation_plan.md`](../implementation-plans/BUG-004/implementation_plan.md)


## Source references and excerpts

### Evidence 1: `repeater/airtime.py` lines 10–28

[Open source path](https://github.com/openhop-dev/openhop_repeater/blob/dev/repeater/airtime.py#L10-L28)

```text
   10 | class AirtimeManager:
   11 |     def __init__(self, config: dict):
   12 |         self.config = config
   13 |         self.radio_config = config.get("radio", {})
   14 |         self.max_airtime_per_minute = config.get("duty_cycle", {}).get(
   15 |             "max_airtime_per_minute", 3600
   16 |         )
   17 | 
   18 |         # Store radio settings for airtime calculations
   19 |         self.spreading_factor = self.radio_config.get("spreading_factor", 7)
   20 |         self.bandwidth = self.radio_config.get("bandwidth", 125000)
   21 |         self.coding_rate = self.radio_config.get("coding_rate", 5)
   22 |         self.preamble_length = self.radio_config.get("preamble_length", 8)
   23 | 
   24 |         # Track airtime in rolling window
   25 |         self.tx_history = []  # [(timestamp, airtime_ms), ...]
   26 |         self.window_size = 60  # seconds
   27 |         self.total_airtime_ms = 0
   28 |         self.total_rx_airtime_ms = 0
```

### Evidence 2: `repeater/config_manager.py` lines 76–149

[Open source path](https://github.com/openhop-dev/openhop_repeater/blob/dev/repeater/config_manager.py#L76-L149)

```text
   76 |     def _apply_live_radio_config(self) -> bool:
   77 |         radio = getattr(self.daemon, "radio", None)
   78 |         if radio is None:
   79 |             logger.warning("Radio not available for live update")
   80 |             return False
   81 | 
   82 |         radio_cfg = self._get_live_radio_snapshot()
   83 | 
   84 |         try:
   85 |             if hasattr(radio, "configure_radio"):
   86 |                 if hasattr(radio, "radio_config") and isinstance(radio.radio_config, dict):
   87 |                     radio.radio_config.update(radio_cfg)
   88 | 
   89 |                 applied = radio.configure_radio(
   90 |                     frequency=radio_cfg["frequency"],
   91 |                     bandwidth=radio_cfg["bandwidth"],
   92 |                     spreading_factor=radio_cfg["spreading_factor"],
   93 |                     coding_rate=radio_cfg["coding_rate"],
   94 |                 )
   95 |                 if not applied:
   96 |                     logger.warning("Live radio reconfiguration failed")
   97 |                     return False
   98 |             else:
   99 |                 current_frequency = getattr(radio, "frequency", None)
  100 |                 current_bandwidth = getattr(radio, "bandwidth", None)
  101 |                 current_spreading_factor = getattr(radio, "spreading_factor", None)
  102 |                 current_coding_rate = getattr(radio, "coding_rate", None)
  103 |                 current_tx_power = getattr(radio, "tx_power", None)
  104 | 
  105 |                 if (
  106 |                     current_frequency != radio_cfg["frequency"]
  107 |                     and hasattr(radio, "set_frequency")
  108 |                     and not radio.set_frequency(radio_cfg["frequency"])
  109 |                 ):
  110 |                     return False
  111 | 
  112 |                 if (
  113 |                     current_tx_power != radio_cfg["tx_power"]
  114 |                     and hasattr(radio, "set_tx_power")
  115 |                     and not radio.set_tx_power(radio_cfg["tx_power"])
  116 |                 ):
  117 |                     return False
  118 | 
  119 |                 coding_rate_changed = current_coding_rate != radio_cfg["coding_rate"]
  120 |                 if coding_rate_changed:
  121 |                     setattr(radio, "coding_rate", radio_cfg["coding_rate"])
  122 | 
  123 |                 if current_spreading_factor != radio_cfg["spreading_factor"]:
  124 |                     if not hasattr(radio, "set_spreading_factor"):
  125 |                         return False
  126 |                     if not radio.set_spreading_factor(radio_cfg["spreading_factor"]):
  127 |                         return False
  128 | 
  129 |                 if current_bandwidth != radio_cfg["bandwidth"]:
  130 |                     if not hasattr(radio, "set_bandwidth"):
  131 |                         return False
  132 |                     if not radio.set_bandwidth(radio_cfg["bandwidth"]):
  133 |                         return False
  134 |                 elif coding_rate_changed:
  135 |                     if hasattr(radio, "set_bandwidth"):
  136 |                         if not radio.set_bandwidth(radio_cfg["bandwidth"]):
  137 |                             return False
  138 |                     elif hasattr(radio, "set_spreading_factor"):
  139 |                         if not radio.set_spreading_factor(radio_cfg["spreading_factor"]):
  140 |                             return False
  141 |                     else:
  142 |                         return False
  143 | 
  144 |             self._sync_repeater_handler_radio_config(radio_cfg)
  145 |             logger.info("Applied live radio configuration to running daemon")
  146 |             return True
  147 |         except Exception as e:
  148 |             logger.error(f"Failed to apply live radio config: {e}", exc_info=True)
  149 |             return False
```

### Evidence 3: `repeater/engine.py` lines 1782–1815

[Open source path](https://github.com/openhop-dev/openhop_repeater/blob/dev/repeater/engine.py#L1782-L1815)

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
```
