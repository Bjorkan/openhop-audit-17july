# BUG-003 — Live duty-cycle limit changes do not update the enforced limit

[← Audit index](../README.md)

> Triple-verification verdict: **confirmed against the supplied snapshots**. The finding survived an independent static runtime trace, executable reproduction and active falsification pass on 18 July 2026.

| Field | Value |
|---|---|
| Classification | **Confirmed defect** |
| Severity | **High** |
| Confidence | **Triple-verified** |
| Area | Duty-cycle enforcement |
| Components | OpenHop Repeater |
| Audit date | 2026-07-17 |
| Independent recheck | 2026-07-18 |
| Status | Open in supplied snapshot |

## TL;DR

The API persists and announces a new duty-cycle limit as applied immediately, but `AirtimeManager` continues enforcing the value copied at process startup.

## What happens now

`AirtimeManager.__init__` caches `max_airtime_per_minute`. `update_duty_cycle_config` changes the shared config and requests a live update, but `ConfigManager.live_update_daemon` has no duty-cycle reload path. Enforcement therefore uses the old numeric limit until restart.

## Expected behaviour / proposed direction

The enforced limit shown in configuration and the runtime limit used by `can_transmit()` must change atomically.

## What needs to change

Add `AirtimeManager.reload_config()` or read a validated immutable snapshot on each decision; invoke it during duty-cycle live updates and report `restart_required` when it cannot be applied.

## Reproduction / verification

Focused check started with 60,000 ms, changed config to 6,000 ms, and showed that a 7,000 ms transmission remained allowed because the cached limit stayed at 60,000 ms.

See [`docs/REVERIFICATION-CHECKS.md`](../docs/REVERIFICATION-CHECKS.md) and the executable check script.

## Triple verification

| Method | Result | Record |
|---|---|---|
| Static runtime trace | **Passed** | The complete reachable path and exact quoted source excerpts in this report were revalidated byte-for-byte against the supplied source trees. |
| Executable reproduction | **Passed** | `test_bug_003_confirmed_live_duty_limit_is_cached` in [`REVERIFICATION-CHECKS.py`](../docs/REVERIFICATION-CHECKS.py). |
| Active falsification | **Passed** | No AirtimeManager refresh exists in live update; the endpoint still exposes an immediate/live-result contract. See [`BASELINE-FALSIFICATION-CHECKS.py`](../docs/BASELINE-FALSIFICATION-CHECKS.py). |

The consolidated baseline matrix and captured results are in [`BASELINE-TRIPLE-VERIFICATION.md`](../docs/BASELINE-TRIPLE-VERIFICATION.md).

## Implementation plan

The former patch sketch has been replaced with a review-oriented plan covering the required repositories/files, implementation sequence, decisions to verify, regression tests, rollout and definition of done.

[Open `implementation_plan.md`](../implementation-plans/BUG-003/implementation_plan.md)


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

### Evidence 2: `repeater/airtime.py` lines 70–97

[Open source path](https://github.com/openhop-dev/openhop_repeater/blob/dev/repeater/airtime.py#L70-L97)

```text
   70 |     def can_transmit(self, airtime_ms: float) -> Tuple[bool, float]:
   71 |         enforcement_enabled = self.config.get("duty_cycle", {}).get("enforcement_enabled", True)
   72 |         if not enforcement_enabled:
   73 |             # Duty cycle enforcement disabled - always allow
   74 |             return True, 0.0
   75 | 
   76 |         now = time.time()
   77 | 
   78 |         # Remove old entries outside window
   79 |         self.tx_history = [(ts, at) for ts, at in self.tx_history if now - ts < self.window_size]
   80 | 
   81 |         # Calculate current airtime in window
   82 |         current_airtime = sum(at for _, at in self.tx_history)
   83 | 
   84 |         if current_airtime + airtime_ms <= self.max_airtime_per_minute:
   85 |             return True, 0.0
   86 | 
   87 |         # Calculate wait time until oldest entry expires
   88 |         if self.tx_history:
   89 |             oldest_ts, oldest_at = self.tx_history[0]
   90 |             wait_time = (oldest_ts + self.window_size) - now
   91 |             return False, max(0, wait_time)
   92 | 
   93 |         return False, 1.0
   94 | 
   95 |     def record_tx(self, airtime_ms: float):
   96 |         self.tx_history.append((time.time(), airtime_ms))
   97 |         self.total_airtime_ms += airtime_ms
```

### Evidence 3: `repeater/web/api_endpoints.py` lines 1925–1978

[Open source path](https://github.com/openhop-dev/openhop_repeater/blob/dev/repeater/web/api_endpoints.py#L1925-L1978)

```text
 1925 |     def update_duty_cycle_config(self):
 1926 |         self._set_cors_headers()
 1927 | 
 1928 |         if cherrypy.request.method == "OPTIONS":
 1929 |             return ""
 1930 | 
 1931 |         try:
 1932 |             self._require_post()
 1933 |             data = cherrypy.request.json or {}
 1934 | 
 1935 |             applied = []
 1936 | 
 1937 |             # Ensure config section exists
 1938 |             if "duty_cycle" not in self.config:
 1939 |                 self.config["duty_cycle"] = {}
 1940 | 
 1941 |             # Update max airtime percentage
 1942 |             if "max_airtime_percent" in data:
 1943 |                 percent = float(data["max_airtime_percent"])
 1944 |                 if percent < 0.1 or percent > 100.0:
 1945 |                     return self._error("Max airtime percent must be 0.1-100.0")
 1946 |                 # Convert percent to milliseconds per minute
 1947 |                 max_airtime_ms = int((percent / 100) * 60000)
 1948 |                 self.config["duty_cycle"]["max_airtime_per_minute"] = max_airtime_ms
 1949 |                 applied.append(f"max_airtime={percent}%")
 1950 | 
 1951 |             # Update enforcement enabled/disabled
 1952 |             if "enforcement_enabled" in data:
 1953 |                 enabled = bool(data["enforcement_enabled"])
 1954 |                 self.config["duty_cycle"]["enforcement_enabled"] = enabled
 1955 |                 applied.append(f"enforcement={'enabled' if enabled else 'disabled'}")
 1956 | 
 1957 |             if not applied:
 1958 |                 return self._error("No valid settings provided")
 1959 | 
 1960 |             # Save to config file and live update daemon
 1961 |             result = self.config_manager.update_and_save(
 1962 |                 updates={}, live_update=True, live_update_sections=["duty_cycle"]
 1963 |             )
 1964 | 
 1965 |             if not result.get("saved", False):
 1966 |                 return self._error(result.get("error", "Failed to save configuration to file"))
 1967 | 
 1968 |             logger.info(f"Duty cycle config updated: {', '.join(applied)}")
 1969 | 
 1970 |             return self._success(
 1971 |                 {
 1972 |                     "applied": applied,
 1973 |                     "persisted": True,
 1974 |                     "live_update": result.get("live_updated", False),
 1975 |                     "restart_required": False,
 1976 |                     "message": "Duty cycle settings applied immediately.",
 1977 |                 }
 1978 |             )
```

### Evidence 4: `repeater/config_manager.py` lines 286–353

[Open source path](https://github.com/openhop-dev/openhop_repeater/blob/dev/repeater/config_manager.py#L286-L353)

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
  308 | 
  309 |             # Also reload advert_helper config if repeater section changed
  310 |             if self.daemon and hasattr(self.daemon, "advert_helper") and self.daemon.advert_helper:
  311 |                 if "repeater" in sections:
  312 |                     if hasattr(self.daemon.advert_helper, "reload_config"):
  313 |                         self.daemon.advert_helper.reload_config()
  314 |                         logger.info("Reloaded AdvertHelper config")
  315 | 
  316 |             # Re-apply the flood reception delay base when delays changed
  317 |             if "delays" in sections and self.daemon and getattr(self.daemon, "dispatcher", None):
  318 |                 delays_cfg = self.daemon.config.get("delays", {})
  319 |                 self.daemon.dispatcher.rx_delay_base = float(delays_cfg.get("rx_delay_base", 0.0))
  320 |                 logger.info(
  321 |                     f"Reloaded flood RX delay base: delays.rx_delay_base="
  322 |                     f"{self.daemon.dispatcher.rx_delay_base}"
  323 |                 )
  324 | 
  325 |             # Re-apply dispatcher path hash mode when mesh section changed
  326 |             if "mesh" in sections and self.daemon and hasattr(self.daemon, "dispatcher"):
  327 |                 mesh_cfg = self.daemon.config.get("mesh", {})
  328 |                 path_hash_mode = mesh_cfg.get("path_hash_mode", 0)
  329 |                 if path_hash_mode not in (0, 1, 2):
  330 |                     logger.warning(
  331 |                         f"Invalid mesh.path_hash_mode={path_hash_mode}, must be 0/1/2; using 0"
  332 |                     )
  333 |                     path_hash_mode = 0
  334 |                 self.daemon.dispatcher.set_default_path_hash_mode(path_hash_mode)
  335 |                 logger.info(f"Reloaded path hash mode: mesh.path_hash_mode={path_hash_mode}")
  336 | 
  337 |             if "radio_type" in sections:
  338 |                 logger.info("radio_type change detected; service restart required")
  339 |                 live_update_ok = False
  340 | 
  341 |             if "kiss" in sections and self._kiss_transport_restart_required():
  342 |                 live_update_ok = False
  343 | 
  344 |             if "radio" in sections:
  345 |                 live_update_ok = self._apply_live_radio_config() and live_update_ok
  346 | 
  347 |             if "http" in sections:
  348 |                 live_update_ok = self._apply_live_http_config() and live_update_ok
  349 | 
  350 |             if "logging" in sections:
  351 |                 live_update_ok = self._apply_live_logging_config() and live_update_ok
  352 | 
  353 |             return live_update_ok
```
